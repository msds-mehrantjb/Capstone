# Asset Inventory & CIA System

The Asset Inventory & CIA System automatically discovers, classifies, and evaluates infrastructure assets within an organization's network. It builds the **Asset Inventory Table**, which becomes the foundation for the ISO 27001 risk assessment workflow.

## Core Capabilities

- Network exploration and subnet discovery
- Host discovery and asset inventory creation
- Server and workstation classification
- Multi-role server detection
- CIA impact classification (Confidentiality, Integrity, Availability)
- Machine learning–assisted role prediction
- Infrastructure clustering and anomaly detection

## Detection Architecture

The system uses a **hybrid detection approach** combining:

1. **Rule-based detection**  
   Uses infrastructure indicators such as installed software, Windows roles, and open ports to identify likely server roles.

2. **Supervised Machine Learning**  
   A **Random Forest classifier** predicts host roles using features derived from:
   - installed software
   - open ports
   - infrastructure indicators
   - service categories

3. **Unsupervised Clustering**  
   A clustering model (e.g., **K-Means or DBSCAN**) groups hosts with similar characteristics to identify infrastructure patterns and anomalies.

Final role assignment is determined by combining:

Rule-Based Detection + ML Prediction + Cluster Analysis

Host Discovery
↓
Feature Extraction
↓
Rule-Based Detection
↓
ML Prediction
↓
Clustering
↓
Final Role Assignment
↓
CIA Resolution

## Command Interface

The Asset Inventory module is controlled through commands:
/explore Discover organizational subnets
/assess Scan subnet and detect hosts
/setstatus Set host status (Active / Inactive / Unknown)
/assignroles Detect server/workstation roles
/editrole Manually change a role
/delete Remove host from inventory
/submit Finalize asset inventory
/reset Clear inventory table
/help Explain module
/commands Show command list


## Host Naming Convention

| Host Type | Format |
|----------|--------|
| Workstation | WS-xx |
| Server | SRV-xx |

Example:
WS-01 → Office Workstation
SRV-01 → Domain Controller
SRV-02 → Web Server


## Role Detection Datasets

- `windows_software-categorized.csv`
- `software_role_signal_matrix.csv`
- `workstation_role_detection_indicators.csv`
- `nist_cia_server_roles_dataset.csv`
- `workstation_cia_dataset.csv`
- `ml_training_dataset.csv`

## CIA Assignment

CIA values are assigned using predefined datasets.

For multi-role servers, the system applies the **Maximum Impact Principle**:

Final CIA = max(C roles), max(I roles), max(A roles)

## Final Workflow
/explore → /assess → /setstatus → /assignroles → CIA resolution → /submit

This module provides the **foundation for ISO 27001 risk analysis**, enabling automated threat identification, vulnerability mapping, and risk register generation.

