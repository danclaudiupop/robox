from robox import Options, Robox

with Robox() as robox:
    page = robox.open("https://httpbin.org/forms/post")
    form = page.get_form()
    form.fill_in("custname", value="foo")
    form.check("topping", values=["Onion"])
    form.choose("size", option="Medium")
    form.fill_in("comments", value="all good in the hood")
    form.fill_in("delivery", value="13:37")
    page = page.submit_form(form)
    assert page.url == "https://httpbin.org/post"


with Robox(options=Options(obey_robotstxt=True)) as robox:
    robox.open("https://news.ycombinator.com/")
