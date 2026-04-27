IRS-PM-2026-05-03-AIS08PT-GRP-SchoolFit-SG.zip

---

## SECTION 1 : PROJECT TITLE
## SchoolFit SG - An Intelligent Decision Support System for Singapore Primary School Selection

---

## SECTION 2 : EXECUTIVE SUMMARY / PAPER ABSTRACT
SchoolFit SG is an intelligent decision support system designed to simplify and improve the primary school selection process for parents in Singapore. Each year, around 38,000 families face a complex and high-stakes decision involving trade-offs between school suitability (e.g., distance, programmes, CCAs) and admission feasibility under the competitive Primary 1 (P1) registration system.

Current tools and platforms provide only fragmented insights—either school information or admission statistics—forcing parents to manually synthesize data and navigate uncertainty. SchoolFit SG addresses this gap by integrating both dimensions into a unified, data-driven recommendation system.

The system combines multiple AI and analytical techniques, including rule-based reasoning, semantic search, and multi-factor scoring, to deliver personalized school recommendations. It evaluates each school along two key axes:

Fit Score (how suitable the school is for the child)
Admission Probability (likelihood of successful entry based on P1 rules and historical balloting data)

Users can input preferences in natural language (e.g., “strong in sports” or “near home”), which are parsed into structured attributes. The system then filters eligible schools, computes weighted suitability scores, models admission eligibility across P1 phases, and estimates admission likelihood using historical data.

The output is a transparent, ranked list of schools accompanied by scores, probabilities, and reasoning traces, enabling parents to make informed and confident decisions.

By consolidating fragmented data and introducing intelligent reasoning, SchoolFit SG transforms a traditionally stressful and opaque process into a personalized, transparent, and data-driven decision experience.

---

## SECTION 3 : CREDITS / PROJECT CONTRIBUTION

| Official Full Name  | Student ID (MTech Applicable)  | Role |
| :------------ |:---------------:| :-----|
| Tan Xian Liang | A0183638U | Project Leader |
| Chua Wentian Carine | A0340663H | Project Member |
| Zhou Lin (Jolin) | A0340258H | Project Member |
| Goh Hong Aik | A0096493N | Project Member |

---

## SECTION 4 : BUSINESS USE CASE & TECHNICAL VIDEOS

Refer to Project file

---

## SECTION 5 : USER GUIDE

`Refer to appendix <Installation & User Guide> in project report at Github Folder: ProjectReport`

### [ 1 ] To run the system using iss-vm

> download pre-built virtual machine from http://bit.ly/iss-vm

> start iss-vm

> open terminal in iss-vm

> $ git clone https://github.com/telescopeuser/Workshop-Project-Submission-Template.git

> $ source activate iss-env-py2

> (iss-env-py2) $ cd Workshop-Project-Submission-Template/SystemCode/clips

> (iss-env-py2) $ python app.py

> **Go to URL using web browser** http://0.0.0.0:5000 or http://127.0.0.1:5000

### [ 2 ] To run the system in other/local machine:
### Install additional necessary libraries. This application works in python 2 only.

> $ sudo apt-get install python-clips clips build-essential libssl-dev libffi-dev python-dev python-pip

> $ pip install pyclips flask flask-socketio eventlet simplejson pandas

---
## SECTION 6 : PROJECT REPORT / PAPER

Refer to Project file

---
