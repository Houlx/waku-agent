"""Career escapes untrusted values before placing them into HTML attributes."""
import subprocess
from pathlib import Path


def test_career_escapes_text_and_attribute_delimiters():
    root = Path(__file__).resolve().parents[2]
    script = r"""
const fs = require('fs');
const vm = require('vm');
const assert = require('assert');
const context = vm.createContext({});
vm.runInContext(fs.readFileSync('waku/ops/static/career/ui.js', 'utf8'), context);
context.input = String.fromCharCode(38, 60, 62, 34, 39);
assert.strictEqual(vm.runInContext('esc(input)', context), '&amp;&lt;&gt;&quot;&#39;');
context.input = String.fromCharCode(34) + ' onclick=' + String.fromCharCode(34) + 'attack';
assert.strictEqual(vm.runInContext('CA.link(input, "#jobs/<x>")', context),
    '<a href="#jobs/&lt;x&gt;">&quot; onclick=&quot;attack</a>');
    """
    subprocess.run(['node', '-e', script], cwd=root, check=True)
