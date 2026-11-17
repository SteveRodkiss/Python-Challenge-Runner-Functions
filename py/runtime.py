"""Runs student code inside Pyodide. Loaded by js/worker.js.

input() cannot block inside a browser worker without special server headers, so
the program is re-run from the start with the answers collected so far
(random is seeded so reruns behave the same). When an answer is missing,
run() returns needInput=True and the page asks the student for it.
"""
import ast
import builtins
import json
import linecache
import random
import re
import reprlib
import sys
import time
import traceback
import types

MAX_STEPS = 3000
MAX_OUTPUT = 200_000
FILENAME = "<user>"


class NeedInput(BaseException):
    pass


class StepLimit(BaseException):
    pass


class OutputLimit(BaseException):
    pass


_repr = reprlib.Repr()
_repr.maxstring = 60
_repr.maxother = 60
_repr.maxlist = _repr.maxtuple = _repr.maxset = 12
_repr.maxdict = 8
_repr.maxlevel = 3

_HIDDEN = (types.ModuleType, types.FunctionType, types.BuiltinFunctionType, types.MethodType, type)


def _variables(namespace):
    result = []
    for name, value in list(namespace.items()):
        if name.startswith("__") or isinstance(value, _HIDDEN):
            continue
        try:
            text = _repr.repr(value)
        except Exception:
            text = "<unprintable>"
        result.append([name, type(value).__name__, text])
    return result


def _is_user_frame(frame):
    code = frame.f_code
    return code.co_filename == FILENAME and (code.co_name == "<module>" or not code.co_name.startswith("<"))


def _format_error(exc, source):
    if isinstance(exc, SyntaxError):
        text = f'  File "main.py", line {exc.lineno}\n'
        if exc.text:
            text += f"    {exc.text.strip()}\n"
        return text + f"{type(exc).__name__}: {exc.msg}", exc.lineno
    linecache.cache[FILENAME] = (len(source), None, source.splitlines(True), FILENAME)
    entries = [e for e in traceback.StackSummary.extract(traceback.walk_tb(exc.__traceback__))
               if e.filename == FILENAME]
    text = ""
    if entries:
        text = "Traceback (most recent call last):\n"
        text += "".join(traceback.format_list(entries)).replace(FILENAME, "main.py")
    text += "".join(traceback.format_exception_only(type(exc), exc)).rstrip()
    return text, (entries[-1].lineno if entries else None)


def _parse_args(test):
    return [ast.literal_eval(a) for a in test.get("args", [])]


def _call_text(function, args):
    return f"{function}({', '.join(repr(a) for a in args)})"


def run(source, inputs_json, debug, emit, call_json="null"):
    inputs = json.loads(inputs_json)
    call = json.loads(call_json)
    random.seed(12345)

    transcript = []
    pending = []
    steps = []
    state = {"chars": 0, "last": time.time(), "next_input": 0}

    def flush():
        current, buf = None, []
        for stream, text in pending:
            if stream != current:
                if buf:
                    emit(current, "".join(buf))
                current, buf = stream, []
            buf.append(text)
        if buf:
            emit(current, "".join(buf))
        pending.clear()
        state["last"] = time.time()

    class Out:
        def __init__(self, stream):
            self.stream = stream

        def write(self, text):
            text = str(text)
            if not text:
                return 0
            state["chars"] += len(text)
            if state["chars"] > MAX_OUTPUT:
                raise OutputLimit()
            transcript.append(text)
            pending.append((self.stream, text))
            if time.time() - state["last"] > 0.03:
                flush()
            return len(text)

        def flush(self):
            pass

    out, err = Out("stdout"), Out("stderr")

    def fake_input(prompt=""):
        out.write(str(prompt))
        index = state["next_input"]
        if index < len(inputs):
            state["next_input"] += 1
            out.write(inputs[index] + "\n")
            return inputs[index]
        raise NeedInput()

    def snapshot(frame):
        stack = []
        while frame is not None:
            if _is_user_frame(frame):
                stack.append(frame)
            frame = frame.f_back
        stack.reverse()
        return [
            {"name": "Global" if f.f_code.co_name == "<module>" else f.f_code.co_name + "()",
             "line": f.f_lineno, "vars": _variables(f.f_locals)}
            for f in stack
        ]

    def tracer(frame, event, arg):
        if not _is_user_frame(frame):
            return None
        if event == "line":
            if len(steps) >= MAX_STEPS:
                raise StepLimit()
            steps.append({"line": frame.f_lineno, "frames": snapshot(frame), "out": state["chars"]})
        return tracer

    namespace = {"__name__": "__main__"}
    result = {"needInput": False, "error": None, "errorLine": None}
    old = (sys.stdout, sys.stderr, builtins.input)
    sys.stdout, sys.stderr, builtins.input = out, err, fake_input
    end = "finished"
    try:
        compiled = compile(source, FILENAME, "exec")
        if debug:
            sys.settrace(tracer)
        exec(compiled, namespace)
        if call:
            function = namespace.get(call["function"])
            if not callable(function):
                raise NameError(f"Your code needs a function called {call['function']}()")
            args = _parse_args(call)
            returned = function(*args)
            out.write(f"\n{_call_text(call['function'], args)} returned {returned!r}\n")
    except NeedInput:
        result["needInput"] = True
    except SystemExit:
        pass
    except StepLimit:
        end, result["error"] = "error", f"Stopped: more than {MAX_STEPS} steps. Is there an endless loop?"
    except OutputLimit:
        end, result["error"] = "error", "Stopped: the program printed too much."
    except BaseException as exc:
        end = "error"
        result["error"], result["errorLine"] = _format_error(exc, source)
    finally:
        sys.settrace(None)
        sys.stdout, sys.stderr, builtins.input = old

    if result["error"]:
        message = result["error"] + "\n"
        transcript.append(message)
        pending.append(("stderr", message))
    flush()

    if debug and not result["needInput"]:
        steps.append({"line": None, "end": end,
                      "frames": [{"name": "Global", "line": None, "vars": _variables(namespace)}],
                      "out": sum(len(t) for t in transcript)})
        result["steps"] = steps
        result["transcript"] = "".join(transcript)
    return json.dumps(result)


def _run_one(compiled, source, function, test):
    printed = []

    class Out:
        def __init__(self, keep):
            self.keep = keep

        def write(self, text):
            text = str(text)
            if self.keep:
                printed.append(text)
                if sum(map(len, printed)) > MAX_OUTPUT:
                    raise OutputLimit()
            return len(text)

        def flush(self):
            pass

    def fake_input(prompt=""):
        raise NeedInput()

    args = _parse_args(test)
    expected = ast.literal_eval(test["expected"])
    result = {"call": _call_text(function, args), "expected": repr(expected), "actual": None}
    old = (sys.stdout, sys.stderr, builtins.input)
    sys.stdout, sys.stderr, builtins.input = Out(True), Out(False), fake_input
    problem = None
    try:
        namespace = {"__name__": "__main__"}
        exec(compiled, namespace)
        target = namespace.get(function)
        if not callable(target):
            problem = f"Your code needs a function called {function}()."
        else:
            actual = target(*args)
            result["actual"] = repr(actual)
            if not (actual == expected and type(actual) is type(expected)):
                problem = "The function returned the wrong value."
    except NeedInput:
        problem = "Your function used input(). It should use its parameters instead."
    except SystemExit:
        problem = "Your code exited early."
    except (OutputLimit, RecursionError):
        problem = "The function printed too much or never stopped."
    except BaseException as exc:
        problem = _format_error(exc, source)[0]
    finally:
        sys.stdout, sys.stderr, builtins.input = old

    result.update(passed=problem is None, output="".join(printed), reason=problem or "")
    return result


def check(source, function, tests_json):
    tests = json.loads(tests_json)
    try:
        compiled = compile(source, FILENAME, "exec")
    except SyntaxError as exc:
        message, line = _format_error(exc, source)
        return json.dumps({"error": message, "errorLine": line, "results": []})
    results = [_run_one(compiled, source, function, t) for t in tests]
    return json.dumps({"error": None, "errorLine": None, "results": results})


