UV ?= uv
PYTEST_SUITES ?= tests/unit/ tests/integration/ tests/system/
ALLURE_RESULTS_DIR ?= allure-results
ALLURE_REPORT_DIR ?= allure-report

.PHONY: merge-cleanup check lint type-check test reports clean-reports

merge-cleanup: check test

check: lint type-check

lint:
	$(UV) run --extra dev ruff check .
	$(UV) run --extra dev black --check .

type-check:
	$(UV) run --extra dev mypy app/

test:
	@set +e; \
	$(UV) run --extra dev pytest $(PYTEST_SUITES) --cov=app --cov-report=xml -p allure_pytest --alluredir=$(ALLURE_RESULTS_DIR); \
	status=$$?; \
	$(MAKE) reports; \
	exit $$status

reports:
	-$(UV) run --extra dev coverage xml --fail-under=0 -o coverage.xml
	-$(UV) run --extra dev coverage html --fail-under=0 -d htmlcov
	-allure generate $(ALLURE_RESULTS_DIR) --clean -o $(ALLURE_REPORT_DIR)

clean-reports:
	rm -rf $(ALLURE_RESULTS_DIR) $(ALLURE_REPORT_DIR) htmlcov coverage.xml junit.xml
