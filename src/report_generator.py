"""
Audit Report Generator module for Electricity Theft Detection.

Generates structured text and downloadable inspection reports for high-risk
consumer accounts identified by the dual-signal ML ensemble and SHAP engine.
"""

from typing import Dict, Any, List
from datetime import datetime


def generate_inspection_report(
    consumer_id: str,
    transformer_id: str,
    risk_score: float,
    supervised_prob: float,
    anomaly_score: float,
    reasons: List[str],
    features: Dict[str, Any] = None
) -> str:
    """Generates an official text audit report for field inspection teams."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S IST")
    report_id = f"AUDIT-{consumer_id}-{int(datetime.now().timestamp())}"
    
    if risk_score >= 0.75:
        priority = "CRITICAL - IMMEDIATE DISPATCH REQUIRED"
    elif risk_score >= 0.50:
        priority = "HIGH - SCHEDULE PHYSICAL INSPECTION"
    else:
        priority = "MEDIUM - MONITORING QUEUE"

    report_lines = [
        "=========================================================================",
        "            SMART GRID ELECTRICITY THEFT INSPECTION REPORT               ",
        "=========================================================================",
        f"Report Reference ID : {report_id}",
        f"Timestamp Generated : {timestamp}",
        f"Target Consumer ID  : {consumer_id}",
        f"Transformer Feeder  : {transformer_id}",
        f"Inspection Priority : {priority}",
        "-------------------------------------------------------------------------",
        "1. DUAL-SIGNAL MACHINE LEARNING RISK METRICS",
        "-------------------------------------------------------------------------",
        f"  Overall Composite Risk Score    : {risk_score:.1%}",
        f"  Supervised Theft Probability    : {supervised_prob:.1%} (XGBoost)",
        f"  Unsupervised Anomaly Score      : {anomaly_score:.1%} (Isolation Forest)",
        "",
        "-------------------------------------------------------------------------",
        "2. EXPLAINABLE AI (SHAP) AUDIT REASONS",
        "-------------------------------------------------------------------------",
    ]

    if reasons:
        for idx, reason in enumerate(reasons, 1):
            report_lines.append(f"  [{idx}] {reason}")
    else:
        report_lines.append("  No specific feature attributions available.")

    report_lines.extend([
        "",
        "-------------------------------------------------------------------------",
        "3. FIELD INSPECTION INSTRUCTIONS & PROTOCOL",
        "-------------------------------------------------------------------------",
        "  1. Verify physical meter seals and check for external shunt wires.",
        "  2. Inspect neutral wire connections and current transformer (CT) ratios.",
        "  3. Check meter optical port for unauthorized firmware modifications.",
        "  4. Record photo evidence and file audit outcome in utility CRM.",
        "=========================================================================",
        "        Issued by Smart Grid Utility Threat Detection Systems           ",
        "========================================================================="
    ])

    return "\n".join(report_lines)
