"""GPU utilisation cache keeps the rich per-device fields the tooltip needs.

`_fetch_gpu_utilization` maps the sidecar's per-GPU dicts into the cache; it must
carry temperature/power through (kept as None when the sidecar omits them, never
faked to 0) alongside utilisation and memory.
"""

from unittest.mock import patch

from duoptimum_hub_services import gpu_cache


def test_fetch_keeps_temperature_and_power():
    fake = [{
        'index': 0, 'utilization': 50, 'memory_used_mb': 1000,
        'temperature_c': 45, 'power_w': 220.5, 'processes': [],
    }]
    with patch('duoptimum_hub_services.gpu_client.fetch_gpus', return_value=fake):
        data = gpu_cache._fetch_gpu_utilization()
    assert data['0']['utilization'] == 50
    assert data['0']['memory_used_mb'] == 1000
    assert data['0']['temperature_c'] == 45
    assert data['0']['power_w'] == 220.5


def test_fetch_temperature_power_none_when_absent():
    fake = [{'index': 1, 'utilization': 0, 'memory_used_mb': 0, 'processes': []}]
    with patch('duoptimum_hub_services.gpu_client.fetch_gpus', return_value=fake):
        data = gpu_cache._fetch_gpu_utilization()
    assert data['1']['temperature_c'] is None
    assert data['1']['power_w'] is None
