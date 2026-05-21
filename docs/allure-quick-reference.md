# 🧭 Allure Pytest Markers — Quick Reference

A compact, developer‑friendly summary of all Allure decorators and dynamic APIs available for structuring, tagging, and enriching pytest tests.

---

## 🏷️ Metadata & Identification

### **Title**  
Set a human‑readable test title.  
- `@allure.title("My title")`  
- `allure.dynamic.title("My title")`  
  [Current page](citation-section://1849405810/8)

Supports parameter interpolation: `{login}`, `{param_id}`.  
  [Current page](citation-section://1849405810/11)

---

### **Description**  
Attach a Markdown‑formatted description.  
- `@allure.description("...")`  
- `allure.dynamic.description("...")`  
  [Current page](citation-section://1849405810/16)

If omitted, Allure uses the test’s docstring.  
  [Current page](citation-section://1849405810/17)

---

### **Tag**  
Assign one or more tags for grouping/filtering.  
- `@allure.tag("api", "smoke")`  
- `allure.dynamic.tag("api")`  
  [Current page](citation-section://1849405810/21)

---

### **Severity**  
Define test importance.  
Allowed values: `trivial`, `minor`, `normal`, `critical`, `blocker`.  
- `@allure.severity(Severity.CRITICAL)`  
- `allure.dynamic.severity("critical")`  
  [Current page](citation-section://1849405810/24)

---

### **Label**  
Attach arbitrary key/value metadata.  
- `@allure.label("layer", "integration")`  
- `allure.dynamic.label("layer", "integration")`  
  [Current page](citation-section://1849405810/26)

This is the underlying mechanism behind many other markers.  
  [Current page](citation-section://1849405810/27)

---

### **Allure ID (TestOps)**  
Link a test to a TestOps test case.  
- `@allure.id("123")`  
- `allure.dynamic.id("123")`  
  [Current page](citation-section://1849405810/35)

---

### **Manual (TestOps)**  
Mark a test as manual in TestOps.  
- `@allure.manual`  
- `allure.dynamic.manual()`  
  [Current page](citation-section://1849405810/37)

---

## 🔗 Links & Issue Tracking

### **Link / Issue / Testcase**  
Attach URLs or issue IDs.  
- `@allure.link("https://example.com", name="Docs")`  
- `@allure.issue("AUTH-123")`  
- `@allure.testcase("TMS-456")`  
  [Current page](citation-section://1849405810/39)

Supports custom link types and link patterns.  
  [Current page](citation-section://1849405810/40)

---

## 🧩 Behavior‑Driven Hierarchy

### **Epic / Feature / Story**  
Define hierarchical grouping for behavior‑based reports.  
- `@allure.epic("Payments")`  
- `@allure.feature("Refunds")`  
- `@allure.story("Refund via card")`  
  [Current page](citation-section://1849405810/45)

---

## 🗂️ Suite‑Based Hierarchy

### **Parent Suite / Suite / Sub Suite**  
Override default suite grouping.  
- `@allure.parent_suite("API Tests")`  
- `@allure.suite("Users")`  
- `@allure.sub_suite("Authentication")`  
  [Current page](citation-section://1849405810/48)

---

## 🪜 Steps

### **Step**  
Define a named step in the report.  
Two styles:

#### Decorator  
```python
@allure.step("Step name")
def do_step(): ...
```
  [Current page](citation-section://1849405810/53)

#### Context Manager  
```python
with allure.step("Step name"):
    ...
```
  [Current page](citation-section://1849405810/56)

Supports parameter interpolation.  
  [Current page](citation-section://1849405810/55)

---

## 🔢 Parameters

### **Dynamic Parameters**  
Add or override parameter display values.  
- `allure.dynamic.parameter("login", "johndoe")`  
  [Current page](citation-section://1849405810/58)

Supports masking and hiding via `allure.parameter_mode`.  
  [Current page](citation-section://1849405810/67)

---

## 📎 Attachments

### **Attach Content**  
```python
allure.attach(body, name="...", attachment_type="text/plain")
```
  [Current page](citation-section://1849405810/72)

Supports media types like `image/png`, `application/json`.  
  [Current page](citation-section://1849405810/77)

---

### **Attach File**  
```python
allure.attach.file("path/to/file.png", name="Screenshot")
```
  [Current page](citation-section://1849405810/85)

---

# 📘 Recommended Marker Conventions for Your Repo

Given your structure (API, UI, integration, e2e), I recommend standardizing on:

- `@allure.epic("API")`, `@allure.epic("UI")`, etc.  
- `@allure.feature("Pets")`, `@allure.feature("Users")`  
- `@allure.story("Create pet")`, `@allure.story("Delete user")`  
- `@allure.severity(Severity.CRITICAL)` for blockers  
- `@allure.tag("smoke")`, `@allure.tag("regression")`  
- `@allure.suite("petstore.api")` to mirror module paths  
- `@allure.label("layer", ["unit" | "integration" | "e2e" ])` for the testing pyramid analysis. this can be extended.
