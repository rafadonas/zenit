import Image from "next/image";
import Link from "next/link";

interface FieldQueueNavigationProps {
  active: "inspection" | "mowing";
}

interface FieldPhotoEvidenceProps {
  alt: string;
  byteSize: number;
  capturedAt?: string;
  dataStatus: "prepared" | "simulated";
  imageSrc: string;
  mediaType: string;
  photoId: string;
}

const queueLinks: Array<{ href: string; id: FieldQueueNavigationProps["active"]; label: string }> = [
  { href: "/photo-reviews", id: "inspection", label: "Inspeção" },
  { href: "/mowing-photo-reviews", id: "mowing", label: "Pós-serviço" },
];

export function FieldQueueNavigation({ active }: FieldQueueNavigationProps) {
  return (
    <nav aria-label="Filas de foto e campo" className="field-queue-nav">
      {queueLinks.map((link) => (
        <Link
          aria-current={active === link.id ? "page" : undefined}
          href={link.href}
          key={link.id}
        >
          {link.label}
        </Link>
      ))}
    </nav>
  );
}

export function FieldPhotoEvidence({
  alt,
  byteSize,
  capturedAt,
  dataStatus,
  imageSrc,
  mediaType,
  photoId,
}: FieldPhotoEvidenceProps) {
  return (
    <figure className="photo-evidence">
      <div className="photo-frame">
        <Image alt={alt} fill sizes="(max-width: 720px) 92vw, 42vw" src={imageSrc} unoptimized />
        <p className="photo-unavailable-note">
          Se a imagem falhar, use os metadados e o ID de evidência abaixo.
        </p>
      </div>
      <figcaption className="photo-meta">
        <span>{mediaType} · {byteSize} bytes</span>
        {capturedAt ? <span>capturada {capturedAt}</span> : null}
        <span>{dataStatus === "prepared" ? "preparada" : "simulada"} · não oficial</span>
        <code title={photoId}>ID {photoId.slice(0, 12)}</code>
      </figcaption>
    </figure>
  );
}
