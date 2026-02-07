export default function OCRProgress({
  status,
  page,
  totalPages,
  message,
}: {
  status: string;
  page: number | null;
  totalPages: number | null;
  message?: string;
}) {
  const percent =
    page && totalPages ? Math.round((page / totalPages) * 100) : 0;

  return (
    <div className="max-w-md space-y-2">
      <p className="text-sm text-gray-600">
        {message}
        {page && totalPages && (
          <> • หน้า {page}/{totalPages}</>
        )}
      </p>
      <div className="h-2 w-full rounded bg-gray-200">
        <div
          className="h-full bg-blue-500 transition-all"
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  );
}

