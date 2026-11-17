# Python Challenge Runner for Functions

An embeddable Python playground for beginners learning functions. It combines Monaco Editor, Pyodide, function tests, an output terminal, and a step-through debugger. Pure HTML/CSS/JS, with no build step.

```
index.html        page (entry point)
editor.html       challenge editor (CRUD for data/challenges.json)
js/challenge-editor.js, css/challenge-editor.css   its code and styles
css/styles.css    styles
js/main.js        wiring, run/debug/stop logic
js/editor.js      Monaco setup
js/runner.js      talks to the Pyodide worker
js/worker.js      Web Worker hosting Pyodide
js/terminal.js    output terminal + inline input()
js/debugger.js    debugger UI (variables, next line, output so far)
data/challenges.json  challenges, loaded on page load (see below)
js/tests.js       renders test results
py/runtime.py     Python-side runner and tracer
```

## Publish and embed

1. Push to GitHub, then **Settings → Pages** → deploy from the `main` branch root.
2. In Google Sites: **Insert → Embed → By URL**, paste `https://<user>.github.io/<repo>/`. Or use **Embed code**:

```html
<iframe src="https://<user>.github.io/<repo>/" width="100%" height="700" style="border:0"></iframe>
```

Optional URL parameter: `?theme=light` (default is dark).

## Using the playground

Serve this folder with `python -m http.server`, then open `http://localhost:8000/`. Internet access is needed to load Monaco and Pyodide.

1. Choose a challenge from the dropdown. Read the docstring and complete the function in the editor.
2. Press **Test** to check its return value against sample calls. Use `return`, not just `print`.
3. If a test fails, choose **Debug this test** to step through that call and inspect variables. **Debug** uses the first sample call.

**Run** executes the editor contents without automatically calling the challenge function. Add your own function calls to try them with Run.

The 20 included challenges are arranged approximately from easiest to hardest. The first 16 cover arithmetic, strings, and simple comparisons; the final four cover lists and text processing.

## Challenges and tests

Each challenge in `data/challenges.json`:

```json
{
  "name": "Add Two",
  "function": "add_two",
  "code": "\"\"\"Write a function called add_two() ...\"\"\"\n\ndef add_two(num):\n    pass\n",
  "tests": [
    { "args": ["5"], "expected": "7" }
  ]
}
```

- `name`: the dropdown label. `function` is the name the tests call, and `code` is the starter code whose docstring describes the challenge.
- `args`: an array of strings containing Python literals, one per argument in order (`"5"`, `"'hi'"`, `"[1, 2]"`); use `[]` for no arguments.
- `expected`: a string containing a Python literal for the return value (compared with `==` and the same type, so `7` and `7.0` differ). Use `"'hi'"` for a string or `"None"` for no return value.
- `description` (optional): extra note shown with the test.
- **Test** runs the code and calls the student's function once per test in a fresh namespace. A failed test shows what was returned or the error, and any printed output. Printing does not replace returning the expected value. Tests do not provide answers to `input()`.
- A failed individual test offers **Debug this test**; syntax errors are shown before individual tests run.

## Editing challenges

Open `editor.html` (serve the folder first, e.g. `python -m http.server`, then visit `http://localhost:8000/editor.html`). You can add, edit, duplicate, reorder and delete challenges and their tests.

- **Open file…** (Chrome/Edge): pick `data/challenges.json` in your copy of the repository. **Save** (or Ctrl+S) then writes straight back to it.
- Other browsers: use **Download** and replace `data/challenges.json` with the downloaded file.
- Enter one Python literal per line in **Arguments** and one Python literal in **Expected return value**. Include quotes around string values. The editor checks that each challenge has a name and a function-name-shaped identifier, and that each test has a nonempty expected value; it does not validate Python literals or require tests. Check them before saving.
- Save or download the JSON, then commit and push it to update the live site. The dropdown follows the order in the file.

## Notes

- **Debug** records up to 3000 steps, then lets you step forward/back, play automatically, or drag the slider. Changed variables are highlighted. The editor is read-only while a recorded session is displayed in the Debugger tab.
- During **Run** and **Debug**, `input()` causes the program to re-run with the answers so far (random is seeded so it repeats identically). Avoid relying on the clock in programs that use `input()`.
- **Stop** kills the worker, so endless loops can always be interrupted.
- Needs internet access to load Monaco and Pyodide from jsDelivr. To run locally, serve the folder (e.g. `python -m http.server`); opening `index.html` via `file://` won't work.
- Code is autosaved to `localStorage` per challenge (keyed by challenge name), when the browser allows it. Unchanged starter code isn't stored, and **↺ Reset** restores a challenge's starter code. Renaming a challenge means students' saved code for the old name is no longer found. The selected challenge is saved by its position, so reordering challenges can change which one is selected on the next visit.
