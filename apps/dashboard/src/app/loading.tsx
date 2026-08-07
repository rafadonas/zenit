export default function Loading() {
  return (
    <main className="shell" aria-busy="true">
      <div className="loading-card">
        <span className="loading-mark" aria-hidden="true" />
        <p>Carregando o corredor monitorado…</p>
      </div>
    </main>
  );
}
