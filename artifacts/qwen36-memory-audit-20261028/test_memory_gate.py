import unittest

from memory_gate import resource_gate_reason


class ResourcePolicyTests(unittest.TestCase):
    def setUp(self):
        self.initial = {'swap_used_mib': 2024.25}
        self.normal = {'kernel_pressure_level': 1, 'swap_used_mib': 2024.25,
                       'disk_free_bytes': 100 * 1024**3, 'free_percent': 15}

    def test_observed_normal_fifteen_percent_is_not_a_pressure_failure(self):
        self.assertIsNone(resource_gate_reason(self.normal, self.initial, 0, 0))

    def test_sustained_low_headroom_still_stops_with_normal_kernel_pressure(self):
        sample = {**self.normal, 'free_percent': 9}
        self.assertIsNone(resource_gate_reason(sample, self.initial, 1, 0))
        self.assertEqual(resource_gate_reason(sample, self.initial, 2, 0), 'sustained memory free <=10%')

    def test_warning_is_independent_of_free_percentage(self):
        sample = {**self.normal, 'free_percent': 80, 'kernel_pressure_level': 2}
        self.assertEqual(resource_gate_reason(sample, self.initial, 0, 2), 'sustained warning memory pressure')

    def test_critical_pressure_stops_immediately(self):
        self.assertEqual(resource_gate_reason({**self.normal, 'kernel_pressure_level': 4}, self.initial, 0, 0), 'critical memory pressure')

    def test_swap_growth_and_absolute_stops_remain(self):
        self.assertEqual(resource_gate_reason({**self.normal, 'swap_used_mib': 4072.25}, self.initial, 0, 0), 'swap growth >=2 GiB')
        self.assertEqual(resource_gate_reason({**self.normal, 'swap_used_mib': 16384}, {'swap_used_mib': 16384}, 0, 0), 'swap >=16 GiB')

    def test_disk_stop_remains(self):
        self.assertEqual(resource_gate_reason({**self.normal, 'disk_free_bytes': 10 * 1024**3 - 1}, self.initial, 0, 0), 'disk below 10 GiB')


if __name__ == '__main__':
    unittest.main()
