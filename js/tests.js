/* Renders the results of "Test my code". */
function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

export function renderTests(root, tests, result, onDebug) {
  root.textContent = "";

  if (result.error) {
    root.append(el("div", "test-summary fail", "Your code has an error, so the tests couldn't run."));
    root.append(el("pre", "test-detail stderr", result.error));
    return;
  }

  const passedCount = result.results.filter((r) => r.passed).length;
  const all = passedCount === tests.length;
  root.append(el("div", "test-summary " + (all ? "pass" : "fail"),
    all ? `🎉 All ${tests.length} tests passed!` : `${passedCount} of ${tests.length} tests passed. Keep going!`));

  tests.forEach((test, i) => {
    const r = result.results[i];
    const card = el("div", "test-card " + (r.passed ? "pass" : "fail"));
    const head = el("div", "test-head");
    head.append(el("span", "", `${r.passed ? "✔" : "✘"} Test ${i + 1}`));
    head.append(el("span", "test-inputs", r.call));
    card.append(head);
    card.append(el("div", "test-want", `Should return ${r.expected}` + (test.description ? ` — ${test.description}` : "")));

    if (!r.passed) {
      card.append(el("div", "test-label", r.reason));
      if (r.actual !== null) card.append(el("div", "test-label", `It returned ${r.actual}`));
      if (r.output) card.append(el("pre", "test-detail", r.output));
      const btn = el("button", "btn small accent", "🐞 Debug this test");
      btn.onclick = () => onDebug(test.args || []);
      card.append(btn);
    }
    root.append(card);
  });
}
