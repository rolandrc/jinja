import math

import pytest

from jinja2 import Environment
from jinja2.exceptions import UndefinedError
from jinja2.nativetypes import NativeEnvironment
from jinja2.nativetypes import NativeTemplate
from jinja2.runtime import Undefined


@pytest.fixture
def env():
    return NativeEnvironment()


@pytest.fixture
def regular_env():
    return Environment()


def test_is_defined_native_return(env):
    t = env.from_string("{{ missing is defined }}")
    assert not t.render()


def test_undefined_native_return(env):
    t = env.from_string("{{ missing }}")
    assert isinstance(t.render(), Undefined)


def test_adding_undefined_native_return(env):
    t = env.from_string("{{ 3 + missing }}")

    with pytest.raises(UndefinedError):
        t.render()


def test_cast_int(env):
    t = env.from_string("{{ value|int }}")
    result = t.render(value="3")
    assert isinstance(result, int)
    assert result == 3


def test_list_add(env):
    t = env.from_string("{{ a + b }}")
    result = t.render(a=["a", "b"], b=["c", "d"])
    assert isinstance(result, list)
    assert result == ["a", "b", "c", "d"]


def test_multi_expression_add(env):
    t = env.from_string("{{ a }} + {{ b }}")
    result = t.render(a=["a", "b"], b=["c", "d"])
    assert not isinstance(result, list)
    assert result == "['a', 'b'] + ['c', 'd']"


def test_loops(env):
    t = env.from_string("{% for x in value %}{{ x }}{% endfor %}")
    result = t.render(value=["a", "b", "c", "d"])
    assert isinstance(result, str)
    assert result == "abcd"


def test_loops_with_ints(env):
    t = env.from_string("{% for x in value %}{{ x }}{% endfor %}")
    result = t.render(value=[1, 2, 3, 4])
    assert isinstance(result, int)
    assert result == 1234


def test_loop_look_alike(env):
    t = env.from_string("{% for x in value %}{{ x }}{% endfor %}")
    result = t.render(value=[1])
    assert isinstance(result, int)
    assert result == 1


@pytest.mark.parametrize(
    ("source", "expect"),
    (
        ("{{ value }}", True),
        ("{{ value }}", False),
        ("{{ 1 == 1 }}", True),
        ("{{ 2 + 2 == 5 }}", False),
        ("{{ None is none }}", True),
        ("{{ '' == None }}", False),
    ),
)
def test_booleans(env, source, expect):
    t = env.from_string(source)
    result = t.render(value=expect)
    assert isinstance(result, bool)
    assert result is expect


def test_variable_dunder(env):
    t = env.from_string("{{ x.__class__ }}")
    result = t.render(x=True)
    assert isinstance(result, type)


def test_constant_dunder(env):
    t = env.from_string("{{ true.__class__ }}")
    result = t.render()
    assert isinstance(result, type)


def test_constant_dunder_to_string(env):
    t = env.from_string("{{ true.__class__|string }}")
    result = t.render()
    assert not isinstance(result, type)
    assert result in {"<type 'bool'>", "<class 'bool'>"}


def test_string_literal_var(env):
    t = env.from_string("[{{ 'all' }}]")
    result = t.render()
    assert isinstance(result, str)
    assert result == "[all]"


def test_string_top_level(env):
    t = env.from_string("'Jinja'")
    result = t.render()
    assert result == "Jinja"


def test_tuple_of_variable_strings(env):
    t = env.from_string("'{{ a }}', 'data', '{{ b }}', b'{{ c }}'")
    result = t.render(a=1, b=2, c="bytes")
    assert isinstance(result, tuple)
    assert result == ("1", "data", "2", b"bytes")


def test_concat_strings_with_quotes(env):
    t = env.from_string("--host='{{ host }}' --user \"{{ user }}\"")
    result = t.render(host="localhost", user="Jinja")
    assert result == "--host='localhost' --user \"Jinja\""


def test_no_intermediate_eval(env):
    t = env.from_string("0.000{{ a }}")
    result = t.render(a=7)
    assert isinstance(result, float)
    # If intermediate eval happened, 0.000 would render 0.0, then 7
    # would be appended, resulting in 0.07.
    assert math.isclose(result, 0.0007)


def test_spontaneous_env():
    t = NativeTemplate("{{ true }}")
    assert isinstance(t.environment, NativeEnvironment)


def test_do_not_repeat_nodes(env):
    """`native_concat` duplicated the first two nodes if it got a list."""
    t = env.from_string(
        """
        {%- macro m(b) -%}
            {{- 'a' -}}
            {%- if b -%}
                {#- The `if` stops the optimizer from joining the strings. -#}
                {#- This macro has to produce multiple nodes. -#}
                {{- 'b' -}}
            {%- endif -%}
            {{- 'c' -}}
        {%- endmacro -%}
        {{- m(true) -}}
    """
    )
    result = t.render()
    # This produced "ababc".
    assert result == "abc"


def test_macro_still_works_with_strings(env, regular_env):
    code = """
        {%- macro m(v) -%}
            start{{ v }}middle{{ v }}end
        {%- endmacro -%}
        {{- m(data) -}}
    """
    template_native = env.from_string(code)
    template_regular = regular_env.from_string(code)
    data = "test"
    result_native = template_native.render(data=data)
    result_regular = template_regular.render(data=data)
    assert result_native == result_regular == "starttestmiddletestend"


def test_macro_returns_int(env):
    t = env.from_string(
        """
        {%- macro m() -%}
            {{- 123 -}}
        {%- endmacro -%}
        {{- m() * 2 -}}
    """
    )
    result = t.render()
    # If the macro returns a string, this is `123123`.
    assert result == 246


def test_macro_returns_list(env):
    t = env.from_string(
        """
        {%- macro m(x) -%}
            {{- x[1] -}}
        {%- endmacro -%}
        {{- m(data)[1] -}}
    """
    )
    data = [[1, 2], [3, 4]]
    result = t.render(data=data)
    assert result == 4


def test_for_recursive_still_works_with_strings(env, regular_env):
    code = """
        {%- for item in data recursive -%}
            {{- item.value -}}
            {%- if item.children -%}
                {{- loop(item.children) -}}
            {%- endif -%}
        {%- endfor -%}
    """
    data = [
        {"value": "0"},
        {
            "value": "1",
            "children": [
                {"value": "2"},
                {"value": "3"},
            ],
        },
        {
            "value": "4",
            "children": [
                {"value": "5"},
            ],
        },
        {"value": "6"},
    ]
    template_native = env.from_string(code)
    template_regular = regular_env.from_string(code)
    result_native = template_native.render(data=data)
    result_regular = template_regular.render(data=data)
    assert result_native == result_regular == "0123456"


def test_recursive_with_native_type(env):
    t = env.from_string(
        """
        {%- for item in data recursive -%}
            {%- if item.child -%}
                {{- item.value + loop(item.child) -}}
            {%- else -%}
                {{- item.value -}}
            {%- endif -%}
        {%- endfor -%}
    """
    )
    data = [
        {
            "value": 1,
            "child": [
                {"value": 2},
            ],
        },
    ]
    result = t.render(data=data)
    assert result == 3
