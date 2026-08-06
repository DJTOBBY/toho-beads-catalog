/**
 * Structured data, emitted inline.
 *
 * A plain <script> rather than next/script: the export has to carry the JSON in
 * the HTML a crawler receives, and the loading strategies exist to keep things
 * out of it.
 */
export function JsonLd({ data }: { data: Record<string, unknown> }) {
  return (
    <script
      type="application/ld+json"
      // "<" is escaped so a colour word or note can never close the script tag.
      dangerouslySetInnerHTML={{ __html: JSON.stringify(data).replace(/</g, "\\u003c") }}
    />
  );
}
