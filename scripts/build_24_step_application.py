from __future__ import annotations

import copy
import hashlib
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W14 = "http://schemas.microsoft.com/office/word/2010/wordml"
XML = "http://www.w3.org/XML/1998/namespace"
NS = {"w": W, "w14": W14}

ET.register_namespace("w", W)
ET.register_namespace("w14", W14)
ET.register_namespace("xml", XML)


STEPS = [
    (1, "问题提出", "提出甜度差异问题，记录初始判断", "10分钟", "问题40%+判断30%+记录30%", 3),
    (2, "概念学习", "提问学习甜味剂与甜味感知概念", "15分钟", "概念40%+完整30%+规范30%", 4),
    (3, "证据追问", "提取结论、证据和文献并继续追问", "15分钟", "结论30%+证据40%+追问30%", 4),
    (4, "样本分类", "查询四种样本并识别类别与特点", "20分钟", "分类40%+完整30%+比较30%", 4),
    (5, "身份核查", "核对名称、分子式、结构及标识符", "20分钟", "身份40%+结构40%+记录20%", 4),
    (6, "甜度查证", "记录公开甜度、条件、来源和缺失项", "20分钟", "数据30%+溯源40%+条件30%", 4),
    (7, "结构比较", "比较结构和性质并提出甜味假设", "20分钟", "比较30%+分析40%+审慎30%", 4),
    (8, "知识总结", "修正判断并提出后续预测问题", "15分钟", "修正30%+总结40%+问题30%", 5),
    (9, "预测排序", "预测四种样本甜度排序并说明依据", "10分钟", "排序30%+依据40%+记录30%", 3),
    (10, "输入核对", "核对SMILES、立体化学和目标物质", "15分钟", "结构50%+核对30%+规范20%", 4),
    (11, "第一组预测", "提交蔗糖和赤藓糖醇并记录结果", "20分钟", "操作30%+结果40%+记录30%", 4),
    (12, "第二组预测", "提交糖精和三氯蔗糖并记录结果", "20分钟", "操作30%+结果40%+记录30%", 4),
    (13, "结果比较", "比较分类、甜味概率和相对甜度", "20分钟", "概念40%+比较30%+解释30%", 5),
    (14, "模型解释", "分析描述符和特征贡献，提出假设", "15分钟", "读取30%+解释40%+边界30%", 4),
    (15, "证据对照", "对照公开资料并分析差异与不可比项", "20分钟", "证据30%+分析40%+审慎30%", 5),
    (16, "边界分析", "修订排序并总结输入、数据和模型局限", "15分钟", "修订30%+局限40%+反思30%", 5),
    (17, "任务定义", "选择母体并明确骨架、位置和性质约束", "10分钟", "目标30%+约束40%+可行30%", 3),
    (18, "母体分析", "识别可能影响甜味的母体结构特征", "15分钟", "证据30%+特征40%+记录30%", 4),
    (19, "智能设计", "向SweetSeek提问并获得一个候选结构", "20分钟", "提示30%+约束30%+理由40%", 4),
    (20, "候选审查", "检查结构和约束并记录修改理由", "20分钟", "审查40%+判断30%+理由30%", 4),
    (21, "结构绘制", "绘制并检查候选结构及SMILES", "20分钟", "结构50%+检查30%+表达20%", 5),
    (22, "对照预测", "同条件预测母体与候选并记录结果", "20分钟", "条件30%+结果40%+记录30%", 5),
    (23, "候选评价", "比较结果并判断是否支持设计假设", "15分钟", "比较30%+判断40%+边界30%", 4),
    (24, "报告反思", "总结依据、结果、局限和验证方向", "15分钟", "内容40%+论证30%+反思30%", 5),
]


AI_TEXT = (
    "本实验将检索增强问答、甜味专业数据库、机器学习分类与回归、特征贡献解释和分子编辑器贯穿于学习全过程。"
    "学生不是被动接受答案，而是通过追问证据、核对结构、比较预测、审查候选和反思模型边界，与人工智能开展连续交互，形成可追溯的学习记录。"
)

INDUSTRY_TEXT = (
    "实验模拟食品研发中的甜味剂筛选与配方前期论证任务：从研发问题定义和公开资料调研出发，完成原料身份核查、结构输入、计算预测、结果解释、候选优化和决策报告。"
    "学生在虚拟环境中体验食品研发人员、数据分析人员和分子设计人员的协同工作方式，并认识安全评价、感官验证和法规审查仍需由后续专业环节完成。"
)

DETAIL_TEXTS = [
    "模块一为甜味知识学习。学生围绕甜度差异提出问题，借助SweetSeek学习基本概念并追问证据，再进入SweetMeta核对蔗糖、赤藓糖醇、糖精和三氯蔗糖的身份、结构与公开甜度记录，最终形成结构与性质比较表并修正初始判断。",
    "模块二为甜度预测与结果解释。学生先独立给出样本排序，再提交经核对的SMILES，分别记录甜味分类、甜味概率、相对甜度估计、理化性质和主要特征贡献。随后将模型结果与公开证据对照，区分分类概率与甜度强度，并分析测定条件和模型误差带来的局限。",
    "模块三为候选甜味分子智能设计。学生选择母体分子并设定结构约束，结合证据和预测提出设计问题，由SweetSeek生成一个候选结构。学生需审查并绘制该结构，在相同模型条件下完成母体与候选对照预测，判断模型输出是否支持设计假设，最后提交包含模型边界和验证方案的实验报告。",
]

RESULT_TEXTS = [
    "在知识学习阶段，学生能够形成可核查的概念、结构和证据记录。由于公开相对甜度受到参照物、浓度、介质和测定方法影响，不同来源的数值可能一致、存在偏差或不可直接比较；合理结论应保留这些条件信息。",
    "在预测阶段，不同结构输入可能产生甜味或非甜味分类、不同甜味概率和不同相对甜度估计。预测与公开资料一致时，可说明模型对该案例具有一定解释力；不一致时，应从结构表达、训练数据覆盖、实验条件和模型误差等方面分析原因，而不能简单判定资料或模型错误。",
    "在设计阶段，候选分子可能表现为预测改善、变化不明显、结果变差或结构无法有效解析。最终结论应以母体对照和证据链为基础，将候选分子定位为待验证的虚拟设计结果。通过本实验，学生能够了解人工智能在食品风味预测、配方优化和新产品设计中的前沿应用，提升证据分析、模型应用和跨学科创新实践能力。",
]


def qn(namespace: str, local: str) -> str:
    return f"{{{namespace}}}{local}"


def node_text(element: ET.Element) -> str:
    return "".join(text.text or "" for text in element.findall(".//w:t", NS))


def make_id(seed: str) -> str:
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:8].upper()


def set_paragraph_text(paragraph: ET.Element, text: str, run_properties: ET.Element | None = None) -> None:
    ppr = paragraph.find("w:pPr", NS)
    for child in list(paragraph):
        if child is not ppr:
            paragraph.remove(child)

    run = ET.SubElement(paragraph, qn(W, "r"))
    if run_properties is None and ppr is not None:
        run_properties = ppr.find("w:rPr", NS)
    if run_properties is not None:
        run.append(copy.deepcopy(run_properties))
    text_node = ET.SubElement(run, qn(W, "t"))
    if text.startswith(" ") or text.endswith(" "):
        text_node.set(qn(XML, "space"), "preserve")
    text_node.text = text


def set_cell_text(cell: ET.Element, text: str, fallback_rpr: ET.Element | None) -> None:
    paragraph = cell.find("w:p", NS)
    if paragraph is None:
        paragraph = ET.SubElement(cell, qn(W, "p"))
    existing_run = paragraph.find("w:r", NS)
    rpr = existing_run.find("w:rPr", NS) if existing_run is not None else fallback_rpr
    set_paragraph_text(paragraph, text, rpr)


def update_row_ids(row: ET.Element, row_number: int) -> None:
    row.set(qn(W14, "paraId"), make_id(f"row-{row_number}"))
    for index, paragraph in enumerate(row.findall(".//w:p", NS)):
        paragraph.set(qn(W14, "paraId"), make_id(f"row-{row_number}-p-{index}"))
        paragraph.set(qn(W14, "textId"), "77777777")


def keep_row_together(row: ET.Element) -> None:
    trpr = row.find("w:trPr", NS)
    if trpr is None:
        trpr = ET.Element(qn(W, "trPr"))
        row.insert(0, trpr)
    if trpr.find("w:cantSplit", NS) is None:
        trpr.append(ET.Element(qn(W, "cantSplit")))


def patch_document(document_xml: bytes) -> bytes:
    root = ET.fromstring(document_xml)

    tables = root.findall(".//w:tbl", NS)
    step_table = next(
        table
        for table in tables
        if len(table.findall("w:tblGrid/w:gridCol", NS)) == 7
        and "步骤序号" in node_text(table)
    )
    rows = step_table.findall("w:tr", NS)
    if len(rows) != 5:
        raise RuntimeError(f"Expected 5 source rows in the step table, found {len(rows)}")

    first_body = rows[1]
    body_template = rows[2]
    first_cell_run = first_body.find("w:tc/w:p/w:r/w:rPr", NS)

    keep_row_together(rows[0])

    for old_row in rows[1:]:
        step_table.remove(old_row)

    for index, step in enumerate(STEPS):
        row = copy.deepcopy(first_body if index == 0 else body_template)
        update_row_ids(row, step[0])
        keep_row_together(row)
        cells = row.findall("w:tc", NS)
        if len(cells) != 7:
            raise RuntimeError(f"Expected 7 cells in row {index + 1}, found {len(cells)}")
        values = [str(step[0]), step[1], step[2], step[3], step[4], str(step[5])]
        for cell, value in zip(cells[:6], values):
            set_cell_text(cell, value, first_cell_run)
        step_table.append(row)

    # Fill the explicit step-count blank without rebuilding its paragraph.
    for paragraph in root.findall(".//w:p", NS):
        if "学生交互性操作" in node_text(paragraph) and "，共" in node_text(paragraph):
            spaces = [t for t in paragraph.findall(".//w:t", NS) if (t.text or "").strip() == ""]
            if not spaces:
                raise RuntimeError("Step-count placeholder was not found")
            spaces[-1].text = "24"
            spaces[-1].attrib.pop(qn(XML, "space"), None)
            break
    else:
        raise RuntimeError("Step-count paragraph was not found")

    # Fill template-provided blank paragraphs after each heading.
    paragraphs = root.findall(".//w:p", NS)
    by_id = {p.get(qn(W14, "paraId")): p for p in paragraphs}
    content_by_id = {
        "1E939C72": AI_TEXT,
        "4414FA38": INDUSTRY_TEXT,
        "11236013": DETAIL_TEXTS[0],
        "15297E10": DETAIL_TEXTS[1],
        "73D5F863": DETAIL_TEXTS[2],
        "54A8A8CA": RESULT_TEXTS[0],
        "65603049": RESULT_TEXTS[1],
        "362957BB": RESULT_TEXTS[2],
    }
    for para_id, content in content_by_id.items():
        paragraph = by_id.get(para_id)
        if paragraph is None:
            raise RuntimeError(f"Template paragraph {para_id} was not found")
        set_paragraph_text(paragraph, content)

    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("Usage: build_24_step_application.py INPUT.docx OUTPUT.docx")

    source = Path(sys.argv[1]).resolve()
    output = Path(sys.argv[2]).resolve()
    if source == output:
        raise SystemExit("Output must differ from the source template")

    expected_hash = "9ce5ffb5cf2c41829b6825523b8bc530436cf681210549a48eb06807ade19854"
    actual_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    if actual_hash != expected_hash:
        raise SystemExit(f"Template hash mismatch: {actual_hash}")

    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(source, "r") as zin, zipfile.ZipFile(output, "w") as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == "word/document.xml":
                data = patch_document(data)
            zout.writestr(item, data)

    print(output)


if __name__ == "__main__":
    main()
