"""ForecastAgent — orchestrates the forecasting pipeline.

fetch_weather → validate_weather → prepare_features → run_model → validate_prediction → generate_explanation

Every step calls a real service, inspects the result and decides what happens next:
repair the data (interpolate gaps, clip out-of-range values), continue with a warning,
or stop the pipeline. The returned agent_steps reflect what actually happened.
"""

import asyncio

import pandas as pd

from app.agent.agent_steps import (
    PIPELINE,
    AgentContext,
    StepFailedError,
    StepHandler,
    execute_step,
    skipped_step,
)
from app.core.constants import POWER_MAX, POWER_MIN, PREDICTION_COLUMNS, WEATHER_COLUMNS
from app.ml.model_adapter import ModelAdapter
from app.schemas.agent import AgentStep, AgentStepId
from app.schemas.forecast import (
    ForecastPoint,
    ForecastRequest,
    ForecastResponse,
    TurbineForecast,
)
from app.services import analysis_service
from app.services.weather_service import WeatherProviderError, WeatherService
from app.utils.datetime import forecast_origin_for, utc_now
from app.utils.validation import ValidationReport, validate_prediction_frame, validate_weather_frame

_WEATHER_SOURCE_LABELS = {
    "mock": "the deterministic demo weather generator",
    "open_meteo": "the Open-Meteo Historical Forecast API",
}


def _raise_on_errors(turbine_id: int, report: ValidationReport) -> None:
    if not report.is_valid:
        details = " ".join(issue.message for issue in report.errors)
        raise StepFailedError(f"Turbine {turbine_id}: {details}")


def _turbine_list(turbine_ids: list[int]) -> str:
    return ", ".join(str(turbine_id) for turbine_id in turbine_ids)


class ForecastAgent:
    # TODO: Replace MockModelAdapter with RealModelAdapter after ML model is ready
    #       (set MODEL_ADAPTER=real — the agent itself does not change).
    def __init__(self, weather_service: WeatherService, model_adapter: ModelAdapter) -> None:
        self._weather = weather_service
        self._model = model_adapter
        self._handlers: dict[AgentStepId, StepHandler] = {
            "fetch_weather": self._fetch_weather,
            "validate_weather": self._validate_weather,
            "prepare_features": self._prepare_features,
            "run_model": self._run_model,
            "validate_prediction": self._validate_prediction,
            "generate_explanation": self._generate_explanation,
        }

    async def run(self, request: ForecastRequest) -> ForecastResponse:
        context = AgentContext(request=request, forecast_origin=forecast_origin_for(request.forecast_date))
        steps: list[AgentStep] = []
        failed_step: AgentStep | None = None

        for step_id in PIPELINE:
            if failed_step is not None:
                steps.append(skipped_step(step_id, failed_step.id))
                continue
            step = await execute_step(step_id, self._handlers[step_id], context)
            steps.append(step)
            if step.status == "failed":
                failed_step = step

        return self._build_response(context, steps, failed_step)

    # --- steps --------------------------------------------------------------------------

    async def _fetch_weather(self, context: AgentContext) -> str:
        request = context.request
        try:
            batch = await self._weather.get_weather(
                request.turbine_ids, context.forecast_origin, request.horizon_hours
            )
        except WeatherProviderError as exc:
            raise StepFailedError(f"Weather could not be retrieved: {exc}") from exc

        context.weather = batch.frames
        context.weather_source = batch.source
        source = _WEATHER_SOURCE_LABELS.get(batch.source, batch.source)
        message = (
            f"Loaded {request.horizon_hours} hourly weather points for turbine(s) "
            f"{_turbine_list(request.turbine_ids)} from {source}."
        )
        if batch.fallback_reason:
            context.warnings.append(
                "Live weather API was unavailable, so demo weather was used instead: "
                f"{batch.fallback_reason}"
            )
            message += " Primary provider failed — the agent switched to the fallback source."
        return message

    async def _validate_weather(self, context: AgentContext) -> str:
        horizon = context.request.horizon_hours
        repaired_values = 0
        anomalies: list[str] = []

        for turbine_id, frame in context.weather.items():
            report = validate_weather_frame(frame, horizon)
            if report.has("missing_values"):
                frame, filled = self._weather.fill_gaps(frame)
                repaired_values += filled
                context.weather[turbine_id] = frame
                report = validate_weather_frame(frame, horizon)
            _raise_on_errors(turbine_id, report)
            anomalies.extend(analysis_service.detect_weather_anomalies(turbine_id, frame))

        context.warnings.extend(anomalies)
        rows = horizon * len(context.weather)
        message = f"{rows} rows passed schema, hourly-continuity and physical-range checks."
        if repaired_values:
            message += f" Interpolated {repaired_values} missing value(s)."
            context.warnings.append(f"Weather input had {repaired_values} gap(s) that were interpolated.")
        if anomalies:
            message += f" Flagged {len(anomalies)} weather anomaly(ies)."
        return message

    async def _prepare_features(self, context: AgentContext) -> str:
        for turbine_id, frame in context.weather.items():
            model_input = frame.loc[:, list(WEATHER_COLUMNS)].copy()
            model_input["timestamp"] = pd.to_datetime(model_input["timestamp"])
            model_input["forecast_origin"] = pd.to_datetime(model_input["forecast_origin"])
            for column in ("wind_speed", "temperature", "latitude", "longitude"):
                model_input[column] = model_input[column].astype("float64")
            context.model_inputs[turbine_id] = model_input.sort_values("timestamp").reset_index(drop=True)

        mean_wind = pd.concat(context.model_inputs.values())["wind_speed"].mean()
        return (
            f"Built {len(context.model_inputs)} model input frame(s) of "
            f"{context.request.horizon_hours} × {len(WEATHER_COLUMNS)} contract columns "
            f"(mean wind {mean_wind:.1f} m/s). Model-specific feature engineering runs inside the model."
        )

    async def _run_model(self, context: AgentContext) -> str:
        request = context.request
        turbine_ids = list(context.model_inputs)
        results = await asyncio.gather(
            *(
                self._model.predict(
                    turbine_id=turbine_id,
                    weather=context.model_inputs[turbine_id],
                    horizon_hours=request.horizon_hours,
                    forecast_origin=context.forecast_origin,
                )
                for turbine_id in turbine_ids
            )
        )
        context.predictions = dict(zip(turbine_ids, results, strict=True))

        versions = sorted(
            {str(v) for frame in results if "model_version" in frame for v in frame["model_version"].unique()}
        )
        context.model_version = ", ".join(versions) or None
        total = sum(len(frame) for frame in results)
        return (
            f"{self._model.name} model ({context.model_version or 'unknown version'}) produced "
            f"{total} hourly predictions for turbine(s) {_turbine_list(turbine_ids)}."
        )

    async def _validate_prediction(self, context: AgentContext) -> str:
        horizon = context.request.horizon_hours
        clipped_total = 0
        anomalies: list[str] = []

        for turbine_id, frame in context.predictions.items():
            report = validate_prediction_frame(frame, horizon)
            _raise_on_errors(turbine_id, report)
            if report.has("out_of_bounds"):
                frame = frame.copy()
                power = frame["predicted_power"]
                clipped_total += int(((power < POWER_MIN) | (power > POWER_MAX)).sum())
                frame["predicted_power"] = power.clip(POWER_MIN, POWER_MAX)
                context.predictions[turbine_id] = frame
            anomalies.extend(analysis_service.detect_power_anomalies(turbine_id, frame))

        context.summary = analysis_service.build_summary(context.predictions)
        context.warnings.extend(anomalies)

        message = (
            f"{horizon * len(context.predictions)} predictions checked: contract columns, "
            f"no NaN, hourly timestamps, values within [{POWER_MIN:g}, {POWER_MAX:g}]."
        )
        if clipped_total:
            message += f" Clipped {clipped_total} out-of-range value(s)."
            context.warnings.append(
                f"Model returned {clipped_total} value(s) outside [0, 1]; they were clipped to physical bounds."
            )
        if anomalies:
            message += f" Flagged {len(anomalies)} operational signal(s)."
        return message

    async def _generate_explanation(self, context: AgentContext) -> str:
        if context.summary is None:
            raise StepFailedError("No validated forecast summary is available to explain.")
        explanation, signals = analysis_service.build_explanation(
            analysis_service.ExplanationInput(
                predictions=context.predictions,
                summary=context.summary,
                horizon_hours=context.request.horizon_hours,
                warning_count=len(context.warnings),
            )
        )
        context.explanation = explanation
        return f"Summarised the forecast from {signals} statistical signal(s) and {len(context.warnings)} warning(s)."

    # --- response -----------------------------------------------------------------------

    def _build_response(
        self,
        context: AgentContext,
        steps: list[AgentStep],
        failed_step: AgentStep | None,
    ) -> ForecastResponse:
        request = context.request
        if failed_step is not None:
            return ForecastResponse(
                forecast_date=request.forecast_date,
                horizon_hours=request.horizon_hours,
                generated_at=utc_now(),
                status="failed",
                summary=None,
                turbines=[],
                agent_steps=steps,
                warnings=context.warnings,
                explanation=f"The agent stopped at “{failed_step.title}”: {failed_step.message}",
                model_version=context.model_version,
                weather_source=context.weather_source,
            )

        return ForecastResponse(
            forecast_date=request.forecast_date,
            horizon_hours=request.horizon_hours,
            generated_at=utc_now(),
            status="completed",
            summary=context.summary,
            turbines=[
                TurbineForecast(turbine_id=turbine_id, points=self._to_points(frame))
                for turbine_id, frame in sorted(context.predictions.items())
            ],
            agent_steps=steps,
            warnings=context.warnings,
            explanation=context.explanation,
            model_version=context.model_version,
            weather_source=context.weather_source,
        )

    @staticmethod
    def _to_points(frame: pd.DataFrame) -> list[ForecastPoint]:
        ordered = frame.loc[:, list(PREDICTION_COLUMNS)].sort_values("timestamp")
        return [
            ForecastPoint(
                timestamp=row.timestamp.to_pydatetime(),
                predicted_power=round(float(row.predicted_power), 4),
                wind_speed=round(float(row.wind_speed), 2),
                temperature=round(float(row.temperature), 2),
            )
            for row in ordered.itertuples(index=False)
        ]
