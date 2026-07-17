# src/convert.py - Dev B: docx to PDF via LibreOffice headless
import os
import shutil
import subprocess
import sys


def find_soffice():
    # try PATH first, then the default Windows install location
    p = shutil.which("soffice")
    if p:
        return p
    win = r"C:\Program Files\LibreOffice\program\soffice.exe"
    if os.path.exists(win):
        return win
    return None


def docx_to_pdf(docx_path="output/cv_filled.docx", out_dir="output"):
    # Try Microsoft Word COM first on Windows if available
    if sys.platform == "win32":
        try:
            import win32com.client
            word = win32com.client.Dispatch("Word.Application")
            word.Visible = False
            
            abs_docx = os.path.abspath(docx_path)
            # Make sure out_dir exists
            os.makedirs(out_dir, exist_ok=True)
            pdf_name = os.path.basename(docx_path).replace(".docx", ".pdf")
            abs_pdf = os.path.abspath(os.path.join(out_dir, pdf_name))
            
            doc = word.Documents.Open(abs_docx)
            doc.SaveAs(abs_pdf, FileFormat=17)  # 17 is wdFormatPDF
            doc.Close()
            word.Quit()
            
            final = os.path.join(out_dir, "cv_final.pdf")
            os.replace(abs_pdf, final)
            return final
        except Exception as e:
            print(f"Microsoft Word PDF conversion failed: {e}. Trying LibreOffice...")

    soffice_path = find_soffice()
    if not soffice_path:
        sys.exit("LibreOffice not found and Microsoft Word conversion failed. Please install LibreOffice or MS Word.")

    cmd = [soffice_path, "--headless", "--convert-to", "pdf",
           "--outdir", out_dir, docx_path]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        raise RuntimeError(f"Conversion failed:\n{result.stderr}")
    pdf = os.path.join(out_dir,
                       os.path.basename(docx_path).replace(".docx", ".pdf"))
    final = os.path.join(out_dir, "cv_final.pdf")
    os.replace(pdf, final)
    return final


if __name__ == "__main__":
    print("Wrote", docx_to_pdf())

