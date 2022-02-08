from robox import DictCache, FileCache, Options, Robox

with Robox(options=Options(cache=DictCache())) as robox:
    p1 = robox.open("https://httpbin.org/get")
    assert not p1.from_cache
    p2 = robox.open("https://httpbin.org/get")
    assert p2.from_cache


with Robox(options=Options(cache=FileCache("./cache"))) as robox:
    p1 = robox.open("https://httpbin.org/get")
    assert not p1.from_cache
    p2 = robox.open("https://httpbin.org/get")
    assert p2.from_cache
