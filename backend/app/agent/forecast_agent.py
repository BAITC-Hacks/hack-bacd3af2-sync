"""ForecastAgent — orchestrates the forecasting pipeline.

fetch_weather → validate_weather → prepare_features → run_model → validate_prediction
    → analyze_result → recompute → generate_explanation

Every step calls a real service, inspects the result and decides what happens next:
repair the data (interpolate gaps, clip out-of-range values), continue with a warning,
or stop the pipeline. analyze_result closes the loop: the agent inspects its own forecast
and, if the input looks doubtful or better input became available, recompute runs the
pipeline once more on fresh input (at most once). The returned agent_steps reflect what
actually happened.
"""

import asyncio
import logging
from typing import Literal

import pandas as pd

from app.agent.agent_steps import (
    NON_FATAL_STEPS,
    PIPELINE,
    STEP_TITLES,
    STEP_TITLES_RU,
    AgentContext,
    StepFailedError,
    StepHandler,
    StepSkippedError,
    execute_step,
    skipped_step,
)
from app.core.constants import (
    INCONSISTENT_SHARE_TRIGGER,
    POWER_MAX,
    POWER_MIN,
    PREDICTION_COLUMNS,
    WEATHER_COLUMNS,
)
from app.ml.model_adapter import ModelAdapter, ModelPredictionError
from app.schemas.agent import AgentStep, AgentStepId
from app.schemas.forecast import (
    ForecastPoint,
    ForecastRequest,
    ForecastResponse,
    TurbineForecast,
)
from app.services import analysis_service
from app.services.llm_explainer import ForecastExplainer, LlmExplainerError
from app.services.weather_service import WeatherBatch, WeatherProviderError, WeatherService
from app.utils.datetime import forecast_origin_for, utc_now
from app.utils.validation import ValidationReport, validate_prediction_frame, validate_weather_frame

logger = logging.getLogger(__name__)

# Pipeline stages re-run by the recompute step (fetch is skipped when fresh weather is ready).
_RECOMPUTE_STAGES: tuple[AgentStepId, ...] = (
    "fetch_weather",
    "validate_weather",
    "prepare_features",
    "run_model",
    "validate_prediction",
)

_WEATHER_SOURCE_LABELS = {
    "mock": "the deterministic demo weather generator",
    "open_meteo": "the Open-Meteo Single Runs API",
    "archive": "the saved Open-Meteo Single Runs archive",
}


def _raise_on_errors(turbine_id: int, report: ValidationReport) -> None:
    if not report.is_valid:
        details = " ".join(issue.message for issue in report.errors)
        raise StepFailedError(f"Turbine {turbine_id}: {details}")


def _model_reported_clips(frame: pd.DataFrame) -> int:
    """Values the model clipped to [0, 1] itself, as reported in frame.attrs["diagnostics"].

    The real ML model clips inside predict_power, so the frame the agent receives is already
    in range; its diagnostics are the only trace. The mock model reports nothing (returns 0).
    """
    diagnostics = frame.attrs.get("diagnostics")
    if not isinstance(diagnostics, dict):
        return 0
    return sum(int(diagnostics.get(key) or 0) for key in ("clipped_below_zero", "clipped_above_one"))


def _turbine_list(turbine_ids: list[int]) -> str:
    return ", ".join(str(turbine_id) for turbine_id in turbine_ids)


class ForecastAgent:
    # The model is injected: MockModelAdapter or RealModelAdapter (MODEL_ADAPTER) — the agent does not change.
    def __init__(
        self,
        weather_service: WeatherService,
        model_adapter: ModelAdapter,
        explainer: ForecastExplainer | None = None,
        explanation_language: Literal["en", "ru"] = "en",
    ) -> None:
        self._weather = weather_service
        self._model = model_adapter
        self._explainer = explainer
        self._language = explanation_language
        self._handlers: dict[AgentStepId, StepHandler] = {
            "fetch_weather": self._fetch_weather,
            "validate_weather": self._validate_weather,
            "prepare_features": self._prepare_features,
            "run_model": self._run_model,
            "validate_prediction": self._validate_prediction,
            "analyze_result": self._analyze_result,
            "recompute": self._recompute,
            "generate_explanation": self._generate_explanation,
        }

    async def run(self, request: ForecastRequest) -> ForecastResponse:
        context = AgentContext(request=request, forecast_origin=forecast_origin_for(request.forecast_date))
        steps: list[AgentStep] = []
        failed_step: AgentStep | None = None

        for step_id in PIPELINE:
            if failed_step is not None:
                steps.append(skipped_step(step_id, failed_step.id, self._language))
                continue
            step = await execute_step(step_id, self._handlers[step_id], context, self._language)
            steps.append(step)
            if step.status == "failed" and step_id not in NON_FATAL_STEPS:
                failed_step = step

        return self._build_response(context, steps, failed_step)

    def _say(self, english: str, russian: str) -> str:
        return russian if self._language == "ru" else english

    # --- steps --------------------------------------------------------------------------

    async def _fetch_weather(self, context: AgentContext) -> str:
        request = context.request
        try:
            batch = await self._weather.get_weather(
                request.turbine_ids, context.forecast_origin, request.horizon_hours
            )
        except WeatherProviderError as exc:
            raise StepFailedError(self._say(f"Weather could not be retrieved: {exc}", f"Не удалось получить погоду: {exc}")) from exc

        self._load_weather(context, batch)
        source = _WEATHER_SOURCE_LABELS.get(batch.source, batch.source)
        message = self._say(
            f"Loaded {request.horizon_hours} hourly weather points for turbine(s) "
            f"{_turbine_list(request.turbine_ids)} from {source}.",
            f"Загружена погода на {request.horizon_hours} ч для турбин {_turbine_list(request.turbine_ids)}. "
            f"Источник: {batch.source}. Проверена доступность архива на момент прогноза."
            if batch.provenance else f"Загружена демонстрационная погода на {request.horizon_hours} ч."
        )
        if batch.fallback_reason:
            context.warnings.append(self._say(
                "Live weather API was unavailable, so the configured fallback was used instead: "
                f"{batch.fallback_reason}",
                f"Погодный API недоступен. Использован резервный источник ({batch.source}): {batch.fallback_reason}"
            ))
            message += self._say(" Primary provider failed, so the agent switched to the fallback source.", " Использован резервный источник.")
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
            anomalies.extend(analysis_service.detect_weather_anomalies(turbine_id, frame, self._language))

        context.warnings.extend(anomalies)
        rows = horizon * len(context.weather)
        message = self._say(f"{rows} rows passed schema, hourly-continuity and physical-range checks.",
                            f"Проверено {rows} строк: структура, почасовая непрерывность и допустимые диапазоны.")
        if repaired_values:
            message += self._say(f" Interpolated {repaired_values} missing value(s).", f" Восстановлено пропусков: {repaired_values}.")
            context.warnings.append(self._say(f"Weather input had {repaired_values} gap(s) that were interpolated.",
                                              f"В погодных данных интерполяцией заполнено пропусков: {repaired_values}."))
        if anomalies:
            message += self._say(f" Flagged {len(anomalies)} weather anomaly(ies).", f" Погодных предупреждений: {len(anomalies)}.")
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
        return self._say(
            f"Built {len(context.model_inputs)} model input frame(s) of "
            f"{context.request.horizon_hours} × {len(WEATHER_COLUMNS)} contract columns "
            f"(mean wind {mean_wind:.1f} m/s). Model-specific feature engineering runs inside the model.",
            f"Подготовлены данные для {len(context.model_inputs)} турбин на {context.request.horizon_hours} ч. "
            f"Средний ветер: {mean_wind:.1f} м/с."
        )

    async def _run_model(self, context: AgentContext) -> str:
        request = context.request
        turbine_ids = list(context.model_inputs)
        try:
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
        except ModelPredictionError as exc:
            raise StepFailedError(self._say(f"Model rejected the request: {exc}", f"Модель отклонила запрос: {exc}")) from exc
        context.predictions = dict(zip(turbine_ids, results, strict=True))

        versions = sorted(
            {str(v) for frame in results if "model_version" in frame for v in frame["model_version"].unique()}
        )
        context.model_version = ", ".join(versions) or None
        total = sum(len(frame) for frame in results)
        return self._say(
            f"{self._model.name} model ({context.model_version or 'unknown version'}) produced "
            f"{total} hourly predictions for turbine(s) {_turbine_list(turbine_ids)}.",
            f"Модель {self._model.name} рассчитала {total} почасовых значений для турбин {_turbine_list(turbine_ids)}."
        )

    async def _validate_prediction(self, context: AgentContext) -> str:
        horizon = context.request.horizon_hours
        clipped_total = 0
        model_clipped_total = 0
        anomalies: list[str] = []

        for turbine_id, frame in context.predictions.items():
            model_clipped_total += _model_reported_clips(frame)
            report = validate_prediction_frame(frame, horizon)
            _raise_on_errors(turbine_id, report)
            if report.has("out_of_bounds"):
                frame = frame.copy()
                power = frame["predicted_power"]
                clipped_total += int(((power < POWER_MIN) | (power > POWER_MAX)).sum())
                frame["predicted_power"] = power.clip(POWER_MIN, POWER_MAX)
                context.predictions[turbine_id] = frame
            anomalies.extend(analysis_service.detect_power_anomalies(turbine_id, frame, self._language))

        context.summary = analysis_service.build_summary(context.predictions)
        context.warnings.extend(anomalies)

        message = self._say(
            f"{horizon * len(context.predictions)} predictions checked: contract columns, "
            f"no NaN, hourly timestamps, values within [{POWER_MIN:g}, {POWER_MAX:g}].",
            f"Проверено {horizon * len(context.predictions)} значений: почасовой шаг, отсутствие пропусков и диапазон [0, 1]."
        )
        # Clipping done by the agent and clipping the model reported doing itself are the same
        # signal for analyze_result, so the loop reacts identically on mock and real models.
        context.clipped_values = clipped_total + model_clipped_total
        if clipped_total:
            message += self._say(f" Clipped {clipped_total} out-of-range value(s).", f" Ограничено значений: {clipped_total}.")
            context.warnings.append(self._say(
                f"Model returned {clipped_total} value(s) outside [0, 1]; they were clipped to physical bounds.",
                f"Агент ограничил {clipped_total} значений мощности диапазоном [0, 1]."
            ))
        if model_clipped_total:
            message += self._say(f" Model reported clipping {model_clipped_total} raw value(s) to [0, 1] itself.",
                                 f" Модель сообщила об ограничении значений: {model_clipped_total}.")
            context.warnings.append(self._say(
                f"Model clipped {model_clipped_total} raw prediction(s) outside [0, 1] to physical bounds "
                "(reported in its diagnostics).",
                f"По диагностике модели {model_clipped_total} значений ограничены диапазоном [0, 1]."
            ))
        if anomalies:
            message += self._say(f" Flagged {len(anomalies)} operational signal(s).", f" Предупреждений: {len(anomalies)}.")
        return message

    async def _analyze_result(self, context: AgentContext) -> str:
        """Inspect the validated forecast and decide whether a recompute is warranted."""
        request = context.request
        reasons: list[str] = []
        codes: list[analysis_service.RecomputeReason] = []
        notes: list[str] = []

        if context.clipped_values:
            reasons.append(self._say(
                f"{context.clipped_values} predicted value(s) fell outside [0, 1] and had to be clipped",
                f"ограничено значений вне диапазона [0, 1]: {context.clipped_values}"
            ))
            codes.append("clipped")

        try:
            refreshed = await self._weather.get_primary_weather(
                request.turbine_ids, context.forecast_origin, request.horizon_hours
            )
        except WeatherProviderError as exc:
            notes.append(self._say(f"Primary weather provider is still unavailable ({exc}); keeping validated weather.",
                                   f"Основной источник всё ещё недоступен ({exc}); сохранена проверенная погода."))
        else:
            if context.weather_fallback_reason:
                context.refreshed_weather = refreshed
                reasons.append(self._say(
                    f"the forecast ran on fallback weather and {refreshed.source} "
                    "answered on retry",
                    "основной источник погоды снова доступен после использования резерва"
                ))
                codes.append("fallback_weather")
            elif self._weather.inputs_changed(context.weather, refreshed):
                context.refreshed_weather = refreshed
                reasons.append(self._say("updated weather inputs became available for the same forecast origin",
                                         "обнаружлены обновлённые погодные входы, доступные на момент прогноза"))
                codes.append("updated_weather")

        consistency = analysis_service.check_physical_consistency(context.predictions)
        if consistency.share >= INCONSISTENT_SHARE_TRIGGER:
            reasons.append(self._say(
                f"{consistency.inconsistent_hours} of {consistency.total_hours} hours ({consistency.share:.0%}) "
                f"contradict the wind ({consistency.calm_but_producing} calm but producing, "
                f"{consistency.windy_but_idle} windy but idle)",
                f"{consistency.inconsistent_hours} из {consistency.total_hours} часов противоречат скорости ветра"
            ))
            codes.append("inconsistent")

        context.recompute_reasons = reasons
        context.recompute_codes = codes
        if reasons:
            return self._say(f"Recompute required ({len(reasons)} trigger(s)): {'; '.join(reasons)}.",
                             f"Нужен пересчёт: {'; '.join(reasons)}.")

        checks = (
            f"{context.clipped_values} clipped value(s), weather from {context.weather_source}, "
            f"{consistency.inconsistent_hours}/{consistency.total_hours} physically inconsistent hours "
            f"({consistency.share:.0%}, trigger at {INCONSISTENT_SHARE_TRIGGER:.0%})"
        )
        return " ".join([self._say(f"No recompute needed: checked {checks}.",
                                   f"Пересчёт не требуется. Несогласованных часов: {consistency.inconsistent_hours}/{consistency.total_hours}; "
                                   f"ограниченных значений: {context.clipped_values}. Проверено обновление погоды."), *notes])

    async def _recompute(self, context: AgentContext) -> str:
        """Run the pipeline once more on fresh input and adopt the result. Never loops."""
        if not context.recompute_reasons:
            raise StepSkippedError(self._say("Not needed: the analysis found no reason to recompute.", "Анализ не выявил причин для пересчёта."))

        context.recompute_performed = True
        sub = AgentContext(request=context.request, forecast_origin=context.forecast_origin)
        stages = _RECOMPUTE_STAGES
        if context.refreshed_weather is not None:
            self._load_weather(sub, context.refreshed_weather)
            stages = _RECOMPUTE_STAGES[1:]

        current = stages[0]
        try:
            for current in stages:
                await self._handlers[current](sub)
        except Exception as exc:  # noqa: BLE001 — any failure keeps the original forecast
            context.recompute_outcome = "the recompute failed, so the original validated forecast was kept."
            context.recompute_outcome_code = "failed"
            raise StepFailedError(self._say(
                f"Recompute failed at “{STEP_TITLES[current]}”: {exc}; kept the original validated forecast.",
                f"Ошибка пересчёта на этапе «{STEP_TITLES_RU[current]}»: {exc}. Сохранён исходный прогноз."
            )) from exc

        before = context.summary.average_power if context.summary else None
        self._adopt(context, sub)
        after = context.summary.average_power if context.summary else None
        change = self._say(f" Average power {before:.3f} → {after:.3f}.",
                           f" Средняя мощность: {before:.3f} → {after:.3f}.") if before is not None and after is not None else ""

        remaining = self._remaining_triggers(sub)
        if remaining:
            context.recompute_outcome = f"the trigger persisted after recompute ({'; '.join(remaining)})."
            context.recompute_outcome_code = "persisted"
            context.warnings.append(self._say(
                f"Recompute did not remove the trigger ({'; '.join(remaining)}); treat this forecast with caution.",
                f"После пересчёта сохранились замечания ({'; '.join(remaining)}). Учитывайте их при планировании."
            ))
            return self._say(f"Recomputed once on fresh input (weather: {sub.weather_source}).{change} Trigger persists: {'; '.join(remaining)}.",
                             f"Выполнен один пересчёт.{change} Замечания сохранились: {'; '.join(remaining)}.")

        context.recompute_outcome = "the recomputed forecast passed all checks and replaced the first result."
        context.recompute_outcome_code = "resolved"
        return self._say(f"Recomputed once on fresh input (weather: {sub.weather_source}).{change} All triggers resolved.",
                         f"Прогноз пересчитан на обновлённых данных.{change} Проверки пройдены.")

    async def _generate_explanation(self, context: AgentContext) -> str:
        if context.summary is None:
            raise StepFailedError(self._say("No validated forecast summary is available to explain.", "Нет проверенного прогноза для объяснения."))
        data = analysis_service.ExplanationInput(
            predictions=context.predictions,
            summary=context.summary,
            horizon_hours=context.request.horizon_hours,
            warning_count=len(context.warnings),
            recompute=analysis_service.RecomputeInfo(
                performed=context.recompute_performed,
                reasons=list(context.recompute_reasons),
                outcome=context.recompute_outcome,
                reason_codes=list(context.recompute_codes),
                outcome_code=context.recompute_outcome_code,
            ),
            language=self._language,
        )
        template, signals = analysis_service.build_explanation(data)

        if self._explainer is None:
            context.explanation, context.explanation_source = template, "template"
            return self._say(f"Template explanation from {signals} signal(s); LLM disabled (OPENAI_API_KEY is not set).",
                             f"Сформировано шаблонное объяснение по {signals} признакам. LLM не подключена.")

        facts = analysis_service.build_explanation_facts(
            data,
            forecast_date=context.request.forecast_date.isoformat(),
            weather_source=context.weather_source,
            model_version=context.model_version,
            warnings=context.warnings,
        )
        try:
            explanation = await self._explainer.explain(facts)
        except LlmExplainerError as exc:
            reason = str(exc)
        except Exception as exc:  # noqa: BLE001 — the explanation must never fail the forecast
            logger.exception("LLM explainer crashed")
            reason = f"unexpected error: {exc}"
        else:
            context.explanation, context.explanation_source = explanation, "llm"
            return self._say(
                f"{self._explainer.name} explained the forecast from {len(facts)} fact groups, "
                f"{len(context.warnings)} warning(s) and the recompute decision.",
                f"{self._explainer.name}: объяснение по {len(facts)} группам фактов, предупреждениям и решению о пересчёте."
            )

        context.explanation, context.explanation_source = template, "template"
        return self._say(f"{self._explainer.name} unavailable ({reason}); used the template explanation ({signals} signal(s)).",
                         f"{self._explainer.name} недоступна ({reason}). Использовано шаблонное объяснение.")

    # --- helpers ------------------------------------------------------------------------

    @staticmethod
    def _load_weather(context: AgentContext, batch: WeatherBatch) -> None:
        context.weather = dict(batch.frames)
        context.weather_source = batch.source
        context.weather_fallback_reason = batch.fallback_reason
        context.weather_provenance = batch.provenance

    @staticmethod
    def _adopt(context: AgentContext, recomputed: AgentContext) -> None:
        """Replace the first-pass result with the recomputed one (its warnings included)."""
        context.weather = recomputed.weather
        context.weather_source = recomputed.weather_source
        context.weather_provenance = recomputed.weather_provenance
        context.weather_fallback_reason = recomputed.weather_fallback_reason
        context.model_inputs = recomputed.model_inputs
        context.predictions = recomputed.predictions
        context.model_version = recomputed.model_version
        context.summary = recomputed.summary
        context.clipped_values = recomputed.clipped_values
        context.warnings = list(recomputed.warnings)

    def _remaining_triggers(self, context: AgentContext) -> list[str]:
        remaining: list[str] = []
        if context.clipped_values:
            remaining.append(self._say(f"{context.clipped_values} value(s) still clipped", f"ограничено значений: {context.clipped_values}"))
        if context.weather_fallback_reason:
            remaining.append(self._say("weather still from the fallback source", "используется резервный источник погоды"))
        consistency = analysis_service.check_physical_consistency(context.predictions)
        if consistency.share >= INCONSISTENT_SHARE_TRIGGER:
            remaining.append(self._say(f"{consistency.share:.0%} of hours still physically inconsistent",
                                       f"{consistency.share:.0%} часов противоречат ветру"))
        return remaining

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
                explanation=self._say(f"The agent stopped at “{failed_step.title}”: {failed_step.message}",
                                       f"Агент остановлен на этапе «{failed_step.title}»: {failed_step.message}"),
                model_version=context.model_version,
                weather_source=context.weather_source,
                weather_provenance=context.weather_provenance,
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
            weather_provenance=context.weather_provenance,
            explanation_source=context.explanation_source,
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
