import * as XLSX from "xlsx";
import { saveAs } from "file-saver";
import { EXCEL_COLUMNS } from "../config/studentFields";

export const downloadTemplate = (categoryLabel) => {
  const worksheet = XLSX.utils.aoa_to_sheet([EXCEL_COLUMNS]);
  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, worksheet, "Students");
  const buffer = XLSX.write(workbook, { bookType: "xlsx", type: "array" });
  saveAs(new Blob([buffer], { type: "application/octet-stream" }), `student_template_${categoryLabel}.xlsx`);
};

export const parseWorkbook = (file) =>
  new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const workbook = XLSX.read(new Uint8Array(event.target.result), { type: "array" });
        const sheet = workbook.Sheets[workbook.SheetNames[0]];
        const rows = XLSX.utils.sheet_to_json(sheet, { defval: "", raw: false });
        resolve(rows.filter((row) => (row.Name || "").toString().trim()));
      } catch (error) {
        reject(error);
      }
    };
    reader.onerror = reject;
    reader.readAsArrayBuffer(file);
  });
