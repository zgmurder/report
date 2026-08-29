from app.schemas.report import ReportContent, ReportSection


class AiClient:
    def generate_report_draft(self, title: str, report_type: str, source_query: dict) -> ReportContent:
        """生成报告草稿。

        第一阶段使用 mock，后续替换为真实 LLM 适配器。AI 输出只作为 draft，不直接覆盖正式报告。
        """
        return ReportContent(
            title=title,
            type=report_type,
            params=source_query,
            sections=[
                ReportSection(
                    id="overview",
                    title="一、总体情况",
                    content="系统已根据所选条件生成总体情况草稿，请结合统计数据核对后使用。",
                    source=["overview_stat"],
                    ai_generated=True,
                ),
                ReportSection(
                    id="type_analysis",
                    title="二、警情类别分析",
                    content="从警情类别看，需重点关注高发类别及环比波动较大的类别。",
                    source=["type_rank"],
                    ai_generated=True,
                ),
                ReportSection(
                    id="risk_judgement",
                    title="三、风险研判与工作建议",
                    content="建议结合重点区域、重点时段和典型警情进一步研判，形成针对性处置建议。",
                    source=["risk_features"],
                    ai_generated=True,
                ),
            ],
        )
