"""Фиксированное поведение, записанное до рефакторинга."""
import json
import pytest
from shop.api import process
from shop.legacy import process as legacy_process, run_file

def add(sku="A", price=1000, qty=1):
    return {"op":"add","sku":sku,"price":price,"qty":qty}

@pytest.mark.parametrize("events, expected", [
    ([], (0,0,0,0,False)),
    ([add()], (1000,0,700,1700,False)),
    ([add(qty=2)], (2000,0,700,2700,False)),
    ([add(price=10000)], (10000,500,700,10200,False)),
    ([add(price=11000)], (11000,550,0,10450,False)),
    ([add(),{"op":"promo","code":" save10 "}], (1000,100,700,1600,False)),
    ([add(price=100),{"op":"promo","code":"FIX500"}], (100,100,700,700,False)),
    ([add(),{"op":"remove","sku":"A"}], (0,0,0,0,False)),
    ([add(),add()], (2000,0,700,2700,False)),
    ([add(),{"op":"checkout"}], (1000,0,700,1700,True)),
    ([add(price=0)], (0,0,700,700,False)),
])
def test_known(events, expected):
    result = process(events)
    assert tuple(result[k] for k in ("subtotal","discount","shipping","total","closed")) == expected
    assert result == legacy_process(events)

@pytest.mark.parametrize("events,message", [
    ([add(qty=0)],"invalid quantity"),([add(price=-1)],"negative price"),
    ([add(sku=" ")],"empty sku"),([add(),add(price=2)],"price mismatch"),
    ([{"op":"remove","sku":"A"}],"unknown sku"),
    ([add(),{"op":"remove","sku":"A","qty":2}],"insufficient quantity"),
    ([{"op":"promo","code":"bad"}],"unknown promo"),
    ([{"op":"checkout"}],"empty cart"),([{"op":"bad"}],"unknown operation"),
    ([add(),{"op":"checkout"},add()],"cart closed"),
])
def test_exceptions(events, message):
    for fn in (process,legacy_process):
        with pytest.raises(ValueError,match=message):
            fn(events)

def test_file(tmp_path, capsys):
    source, target = tmp_path/"in.json", tmp_path/"out.json"
    source.write_text(json.dumps([add()]), encoding="utf-8")
    run_file(source,target)
    assert json.loads(target.read_text(encoding="utf-8")) == process([add()])
    assert '"total": 1700' in capsys.readouterr().out
