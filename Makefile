PYTHON ?= python
IN ?= examples/demo.jsonl
OUT ?= runtime/pred.jsonl
.PHONY: predict serve test evaluate
predict:
	$(PYTHON) -m copilot.cli --input "$(IN)" --output "$(OUT)"
serve:
	$(PYTHON) -m copilot.server
test:
	$(PYTHON) -m unittest discover -s tests -v
evaluate:
	$(PYTHON) -m copilot.evaluate --input data/tickets_valid.jsonl --output reports/validation.json
