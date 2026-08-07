"use client";

export default function ErrorPage({ reset }: { reset: () => void }) {
  return (
    <main className="shell">
      <section className="state-card" role="alert">
        <p className="eyebrow">Falha de comunicação</p>
        <h1>Não foi possível carregar o corredor.</h1>
        <p>A API não respondeu. Os dados não foram substituídos por uma simulação.</p>
        <button className="primary-button" onClick={reset} type="button">
          Tentar novamente
        </button>
      </section>
    </main>
  );
}
