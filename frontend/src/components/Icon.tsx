type Name = 'search' | 'documents' | 'arrow';

const paths: Record<Name, string> = {
  search: 'm21 21-4.4-4.4 M19 10.5a8.5 8.5 0 1 1-17 0 8.5 8.5 0 0 1 17 0',
  documents: 'M8 3H4v18h12v-4 M8 3h8l4 4v10H8V3 M15 3v5h5 M11 11h6 M11 14h6',
  arrow: 'M4 12h16 M14 6l6 6-6 6',
};

export function Icon({ name }: { name: Name }) {
  return (
    <svg
      className="icon"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={paths[name]} />
    </svg>
  );
}
