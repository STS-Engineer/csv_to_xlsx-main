// Run with: node tests/test_ui_script.js. Lightweight DOM contract checks;
// these complement, and do not replace, browser integration tests.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
class Element {
  constructor() {
    this.listeners = {};
    this.attributes = {};
    this.classList = { add() {}, remove() {} };
    this.files = [];
    this.hidden = false;
    this.validity = { valid: true };
  }
  addEventListener(name, fn) { (this.listeners[name] ||= []).push(fn); }
  emit(name, event = {}) {
    event.preventDefault ||= () => { event.prevented = true; };
    for (const fn of this.listeners[name] || []) fn(event);
    return event;
  }
  setCustomValidity(message) { this.validity.valid = !message; }
  setAttribute(key, value) { this.attributes[key] = value; }
  removeAttribute(key) { delete this.attributes[key]; }
  checkValidity() { return true; }
  reportValidity() { this.reported = true; }
}
const ids = ['convert-form', 'customer_name', 'customer_code', 'source-file', 'drop-zone', 'file-status', 'file-error', 'convert-button', 'button-label', 'processing-status'];
const nodes = Object.fromEntries(ids.map(id => [id, new Element()]));
const spinner = new Element();
nodes['convert-button'].querySelector = () => spinner;
nodes.customer_name.selectedOptions = [{ dataset: { code: 'C00250' } }];
const window = new Element();
vm.runInNewContext(fs.readFileSync('static/converter.js', 'utf8'), {
  document: { getElementById: id => nodes[id] }, window,
});
assert.equal(nodes.customer_code.value, 'C00250');
nodes['source-file'].files = [{ name: 'bad.exe', size: 10 }];
nodes['source-file'].emit('change');
assert.equal(nodes['file-error'].hidden, false);
assert.equal(nodes['convert-form'].emit('submit').prevented, true);
nodes['source-file'].files = [{ name: 'empty.csv', size: 0 }];
nodes['source-file'].emit('change');
assert.match(nodes['file-error'].textContent, /empty/);
nodes['drop-zone'].emit('drop', { dataTransfer: { files: [ {}, {} ] } });
assert.match(nodes['file-error'].textContent, /one file/);
nodes['drop-zone'].emit('drop', { dataTransfer: { files: [{ name: '<script>.CSV', size: 1025 }] } });
assert.equal(nodes['file-error'].hidden, true);
assert.equal(nodes['file-status'].textContent, '<script>.CSV · 2 KB');
assert.equal(nodes['convert-form'].emit('submit').prevented, undefined);
assert.equal(nodes['convert-button'].disabled, true);
assert.equal(nodes['convert-form'].attributes['aria-busy'], 'true');
assert.equal(nodes['convert-form'].emit('submit').prevented, true);
window.emit('pageshow');
assert.equal(nodes['convert-button'].disabled, false);
assert.equal(spinner.hidden, true);
assert.equal(nodes['convert-form'].attributes['aria-busy'], undefined);
console.log('PASS: customer code, invalid/empty file validation, multi-file rejection, valid drop, literal filename display, loading state, duplicate-submit guard, pageshow reset');
