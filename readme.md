# Lab 8 — Test Coverage


## 1. Overview

The starter code of Lab 8 is **Lab 3's correct answer**. It implements the file CRUD using REST API (`backend/rest_service.py`), with disk operations in `backend/data_logic`. Meanwhile, `test.py` contains the test cases that are used to evaluate your implementation correctly.

In this lab, your task is to first measure the **test coverage** of the test cases, and then try to add test cases to make sure **the line coverage is >95%**.


## 2. Setup

```bash
pip install -r requirements.txt
```
In this lab, the package `coverage` is required.


## 3. TODO: Coverage Measurement

The file `.coveragerc` specifies the coverage cofiguration. It requires that only the coverage of the file `backend/data_logic.py` is measured.

This command runs the test cases, with coverage information recorded (you don't need to start `rest_service.py`).
```bash
python3 -m coverage run test.py
```

Ths command prints out the overall coverage result (e.g. `90%`).
```bash
python3 -m coverage report -m
```

This command writes the coverage results as an HTML report (`htmlcov/index.html`), so that you can inspect the specific covered/missed lines.
```bash
python3 -m coverage html
```

Overall Ideas:
+ 
+ If you have modified the test cases and want to obtain the new coverage, just rerun the above commands again.

## 4. TODO

Your task is to add new test cases to `test.py`, so that the coverage can reach **>= 95%**.

The overall process is:
1. Run the current tests and measure coverage.
2. Use the HTML report to see which lines are missed.
3. Add new test cases to cover the missed lines.
4. Go back to step 1.

Note that:
+ our current tests exercise the REST API (this is usually called interface testing). 
+ You may also call data_logic functions directly, which is usually called unit testing.

## 5. File structure

```
Lab8/
├── frontend/
├── backend/
│   ├── data_logic.py      # CRUD (coverage target)
│   └── rest_service.py    # Lab 3 REST answer
├── data/
├── test.py
├── .coveragerc
└── requirements.txt
```

