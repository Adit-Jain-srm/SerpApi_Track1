import digest from "@/content/digest.json";
import { Film } from "@/components/film";
import type { DigestFile } from "@/lib/types";

export default function HomePage() {
  return (
    <>
      <h1 className="sr-only">AI Tool Discovery Agent</h1>
      <Film digest={digest as DigestFile} />
    </>
  );
}
