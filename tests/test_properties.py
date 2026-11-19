from copy import deepcopy
import json
import pytest
from hypothesis import given, strategies as st
from shop.core import reduce_event, add_item, remove_item
from shop.model import Cart, Event
from shop.discounts import discount, subtotal
from shop.pricing import quote
from shop.pipeline import process
from shop.legacy import process as legacy
from shop.shell import run_file, main

@given(st.integers(0,100000),st.integers(1,100))
def test_inverse(price,qty):
    c = reduce_event(Cart(),Event("add","A",price,qty))
    assert reduce_event(c,Event("remove","A",qty=qty)) == Cart()

@given(st.integers(0,100000),st.integers(1,100))
def test_purity(price,qty):
    old = Cart()
    event = Event("add","A",price,qty)
    assert reduce_event(old,event) == reduce_event(old,event)
    assert old == Cart()

@given(st.integers(0,100000),st.sampled_from(["","SAVE10","FIX500"]))
def test_discount_bounds(price,code):
    c = reduce_event(reduce_event(Cart(),Event("add","A",price)), Event("promo",code=code))
    assert 0 <= discount(c) <= subtotal(c)
    q = quote(c)
    assert q["total"] == q["subtotal"]-q["discount"]+q["shipping"]

@given(st.lists(st.tuples(st.sampled_from(["A","B","C"]),st.integers(1,10)),max_size=30),
       st.sampled_from(["","SAVE10","FIX500"]))
def test_equivalence(rows,code):
    events = [{"op":"add","sku":sku,"price":1000,"qty":qty} for sku,qty in rows]
    events.append({"op":"promo","code":code})
    before = deepcopy(events)
    assert process(events) == legacy(events)
    assert events == before

@given(st.integers(0,10000),st.integers(0,10000))
def test_order_independent(a,b):
    ea, eb = Event("add","A",a),Event("add","B",b)
    assert reduce_event(reduce_event(Cart(),ea),eb) == reduce_event(reduce_event(Cart(),eb),ea)

def test_all_boundaries():
    c = reduce_event(Cart(),Event("add","A",100,3))
    assert reduce_event(c,Event("remove","A",qty=1)).items[0].qty == 2
    for event in (Event("remove","A",qty=0),Event("remove","A",qty=4),Event("add","A",200)):
        with pytest.raises(ValueError):
            reduce_event(c,event)
    assert discount(c,()) == 0

def test_shell(tmp_path, capsys):
    source, target = tmp_path/"in.json",tmp_path/"out.json"
    source.write_text('[{"op":"add","sku":"A","price":1000}]',encoding="utf-8")
    run_file(source,target)
    assert json.loads(target.read_text(encoding="utf-8"))["total"] == 1700
    main([str(source),"--output",str(target)])
    assert '"total": 1700' in capsys.readouterr().out
