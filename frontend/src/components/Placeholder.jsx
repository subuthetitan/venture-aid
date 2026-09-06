export default function Placeholder({ title, owner, notes }) {
  return (
    <div className="rounded-lg border border-dashed bg-white p-8">
      <p className="text-xs uppercase tracking-wide text-stone-400">Pair {owner}</p>
      <h2 className="mt-1 text-xl font-semibold">{title}</h2>
      <ul className="mt-4 list-disc space-y-1 pl-5 text-sm text-stone-600">
        {notes.map((n) => <li key={n}>{n}</li>)}
      </ul>
    </div>
  );
}
