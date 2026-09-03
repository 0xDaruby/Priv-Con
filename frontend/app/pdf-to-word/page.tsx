import { ConversionTool } from "@/components/conversion/ConversionTool";
import { TOOL_CONFIGS } from "@/lib/constants";

export default function PdfToWordPage() {
  return <ConversionTool config={TOOL_CONFIGS.pdfToWord} />;
}
