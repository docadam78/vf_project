import datetime as dt

from volfitter.adapters.current_time_supplier import CyclingCurrentTimeSupplier


def test_cycling_current_time_supplier_returns_times_in_order_then_cycles_back_to_start():
    time_1 = dt.datetime(2022, 3, 20, 1, 0)
    time_2 = dt.datetime(2022, 3, 20, 2, 0)
    time_3 = dt.datetime(2022, 3, 20, 3, 0)

    victim = CyclingCurrentTimeSupplier([time_1, time_2, time_3])

    assert victim.get_current_time() == time_1
    assert victim.get_current_time() == time_2
    assert victim.get_current_time() == time_3
    assert victim.get_current_time() == time_1
