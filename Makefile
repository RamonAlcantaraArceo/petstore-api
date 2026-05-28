UV ?= uv
PYTEST_SUITES ?= tests
ALLURE_HISTORY_REPORT = allure-history.jsonl
ALLURE_RESULTS_DIR ?= allure-results
ALLURE_REPORT_DIR ?= allure-report
E2E_COVERAGE_DIR ?= .e2e-coverage
FAIL_UNDER ?= 80

.PHONY: merge-cleanup check lint type-check test reports clean-reports

merge-cleanup: check test

check: lint type-check

lint:
	$(UV) run --extra dev ruff check .
	$(UV) run --extra dev black --check .

type-check:
	$(UV) run --extra dev mypy app/

test:
	# Preserve pytest's exit code while still generating reports for failed runs.
	@set +e; \
	$(UV) run --extra dev pytest $(PYTEST_SUITES) --cov-fail-under=0 --cov=app --cov=petstore_core --cov-report=xml --alluredir=$(ALLURE_RESULTS_DIR) --clean-alluredir; \
	status=$$?; \
	$(MAKE) reports; \
	reports_status=$$?; \
	if [ $$status -eq 0 ] && [ $$reports_status -ne 0 ]; then status=$$reports_status; fi; \
	exit $$status

reports:
	# Keep report-generation best-effort so merge-cleanup still returns test status.
	@-allure generate $(ALLURE_RESULTS_DIR) -o $(ALLURE_REPORT_DIR)
	@-$(UV) run --extra dev coverage combine --append $(E2E_COVERAGE_DIR)/.coverage.service*
	@-$(UV) run --extra dev coverage xml --fail-under=0 -o coverage.xml
	@$(UV) run --extra dev coverage html --fail-under=$(FAIL_UNDER) -d htmlcov

clean-reports:
	rm -rf $(ALLURE_RESULTS_DIR) $(ALLURE_REPORT_DIR) $(E2E_COVERAGE_DIR) .allure/$(ALLURE_HISTORY_REPORT) htmlcov coverage.xml junit.xml
