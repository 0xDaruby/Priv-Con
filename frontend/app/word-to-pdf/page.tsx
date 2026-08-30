import { ConversionTool } from "@/components/conversion/ConversionTool";
import { TOOL_CONFIGS } from "@/lib/constants";

export default function WordToPdfPage() {
  return <ConversionTool config={TOOL_CONFIGS.word} />;
}
