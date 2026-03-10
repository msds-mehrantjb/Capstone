# Asset Inventory & CIA System

The **Asset Inventory & CIA System** automatically discovers, classifies, and evaluates infrastructure assets within an organization's network. It builds the **Asset Inventory Table**, which becomes the foundation for the ISO 27001 risk assessment workflow.

## Core Capabilities

- Network exploration and subnet discovery
- Host discovery and asset inventory creation
- Server and workstation classification
- Multi-role server detection
- CIA impact classification (Confidentiality, Integrity, Availability)
- Machine learning–assisted role prediction
- Infrastructure clustering and anomaly detection

---

# Detection Architecture

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

---

# Command Interface

The Asset Inventory module is controlled through commands:
