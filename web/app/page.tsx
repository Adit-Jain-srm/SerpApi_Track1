import digest from "@/content/digest.json";
import { Film } from "@/components/film";
import type { DigestFile } from "@/lib/types";

export default function HomePage() {
  return <Film digest={digest as DigestFile} />;
}
