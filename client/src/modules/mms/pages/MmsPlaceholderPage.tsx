interface Props {
  title: string;
}

export default function MmsPlaceholderPage({ title }: Props) {
  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold text-gray-900">{title}</h1>
      <p className="mt-2 text-sm text-gray-600">
        Mess Management System (MMS) operational interface.
      </p>
    </div>
  );
}
