"""PDF representation of an already-frozen confirmed-observation report."""
import textwrap
import pymupdf as fitz


def report_pdf(report, report_hash):
    pdf=fitz.open()
    page=None;y=0

    def new_page():
        nonlocal page,y
        page=pdf.new_page(width=595,height=842)
        page.insert_text((40,35),'EVIDENCE WORKBENCH | SIH 26261',fontsize=10,color=(.12,.32,.28))
        page.insert_text((40,805),f'Synthetic demonstration | Draft rules | Page {len(pdf)}',fontsize=8,color=(.4,.4,.4))
        y=70

    def paragraph(text,bold=False):
        nonlocal y
        safe=str(text).encode('ascii','replace').decode()
        for line in textwrap.wrap(safe,width=85 if bold else 98) or ['']:
            if page is None or y>760:new_page()
            page.insert_text((40,y),line,fontsize=12 if bold else 10,fontname='hebo' if bold else 'helv')
            y+=17
        y+=9

    new_page()
    paragraph('SYNTHETIC DEMONSTRATION REVIEW REPORT',True)
    paragraph('This is not an official AICTE deficiency report or an approval/rejection decision.')
    paragraph('Institution: '+report['name'],True)
    paragraph('Application: '+report['application_id'])
    paragraph('Evaluation: '+report['evaluation_id'])
    paragraph('Created: '+report['created_at'])
    paragraph('Policy status: '+report['policy_status'])
    paragraph('Manifest SHA-256: '+report['manifest_hash'])
    paragraph('Frozen JSON report SHA-256: '+report_hash)
    findings=report['confirmed_findings']
    paragraph(f'Confirmed observations: {len(findings)}',True)
    if not findings:paragraph('No observations were reviewer-confirmed in this frozen snapshot. This does not establish institutional compliance.')
    for index,f in enumerate(findings,1):
        paragraph(f'{index}. {f["title"]}',True)
        paragraph('Rule: '+f['rule_id']+' | Version: '+f['rule_version'])
        paragraph(f['explanation'])
        paragraph('Required action: '+f['required_action'])
        for evidence in f['evidence']:
            paragraph(f'Evidence document {evidence["document_id"]}, page {evidence["page"]}, fact {evidence["field_id"]}.')
        if not f['evidence']:paragraph('Evidence gap: '+f['reason']+'. Missing/unconfirmed evidence is explicitly identified.')
    data=pdf.tobytes()
    pdf.close()
    return data
