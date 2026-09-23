import tempfile
import unittest
from pathlib import Path
import numpy as np
import pandas as pd
from src.training.models import checked_prediction, save_model, load_model
from src.training.baselines import EmpiricalPowerCurve


class ModelTests(unittest.TestCase):
    def test_corrections_are_counted_and_nonfinite_predictions_fail(self):
        class Stub:
            def predict(self, features):
                return [-.1, .5, 1.2]
        predictions, log = checked_prediction(Stub(), pd.DataFrame({"wind_speed": [0, 5, 10]}))
        np.testing.assert_array_equal(predictions, [0, .5, 1])
        self.assertEqual(log, {"clipped_below_zero": 1, "clipped_above_one": 1})
        class Broken:
            def predict(self, features):
                return [np.nan]
        with self.assertRaises(ValueError):
            checked_prediction(Broken(), pd.DataFrame({"wind_speed": [0]}))

    def test_curve_artifact_roundtrip(self):
        x = pd.DataFrame({"wind_speed": [0., 5., 10.]})
        model = EmpiricalPowerCurve().fit(x, [0., .2, 1.])
        with tempfile.TemporaryDirectory() as folder:
            path = save_model(model, "power_curve", Path(folder))
            np.testing.assert_array_equal(load_model("power_curve", path).predict(x), model.predict(x))


if __name__ == "__main__":
    unittest.main()
