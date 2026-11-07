"use client";

import { useEffect, useRef, useState } from "react";
import type { PDFDocumentLoadingTask, PDFDocumentProxy, PDFPageProxy, RenderTask } from "pdfjs-dist";
import { BACKEND_LIMITS } from "@/lib/constants";
import { HELVETICA_ADVANCES, HELVETICA_ASCENDER, HELVETICA_DESCENDER } from "@/lib/helvetica-metrics";
import { validateWatermarkOptions, type WatermarkOptionFields } from "@/lib/pdf-overlay-options";
import { numericWatermarkPlacement, previewPageWindow, selectedPreviewPage, watermarkImageDimensions, watermarkPlacement, watermarkTextSize, type PreviewSize } from "@/lib/watermark-preview";

interface Props {
  readonly file: File;
  readonly options: WatermarkOptionFields;
  readonly image?: File;
  readonly pages: string;
  readonly pageError?: string;
  readonly onPageCount?: (count: number | undefined) => void;
}

interface DocumentState {
  readonly file: File;
  readonly attempt: number;
  readonly pdf?: PDFDocumentProxy;
  readonly loading?: PDFDocumentLoadingTask;
  readonly error?: string;
}
interface PageState extends PreviewSize { readonly ready?: boolean; readonly error?: string }
interface WindowState {
  readonly pdf: PDFDocumentProxy;
  readonly index: number;
  readonly pages: Readonly<Record<number, PageState>>;
}
interface ImageState extends PreviewSize { readonly file: File; readonly url?: string; readonly error?: string }

const METRICS = { advances: HELVETICA_ADVANCES, ascender: HELVETICA_ASCENDER, descender: HELVETICA_DESCENDER };

/** Rendering never persists document bytes or enables an interactive PDF layer. */
export function PdfWatermarkPreview({ file, options, image, pages, pageError, onPageCount }: Props) {
  const [attempt, setAttempt] = useState(0);
  const [documentState, setDocumentState] = useState<DocumentState>();
  const [windowChoice, setWindowChoice] = useState<{ file: File; index: number }>();
  const [windowState, setWindowState] = useState<WindowState>();
  const [imageState, setImageState] = useState<ImageState>();
  const canvasRefs = useRef(new Map<number, HTMLCanvasElement>());
  const previewRef = useRef<HTMLElement>(null);

  useEffect(() => {
    let stopped = false;
    let loading: PDFDocumentLoadingTask | undefined;
    let timer: ReturnType<typeof setTimeout> | undefined;
    onPageCount?.(undefined);

    const load = async () => {
      try {
        if (file.size <= 0 || file.size > BACKEND_LIMITS.maxFileBytes) throw new Error("file-limit");
        const pdfjs = await import("pdfjs-dist");
        if (stopped) return;
        const data = new Uint8Array(await file.arrayBuffer());
        if (stopped) return;
        pdfjs.GlobalWorkerOptions.workerSrc = `/pdfjs/worker/pdf.worker.min.mjs?v=${pdfjs.version}`;
        loading = pdfjs.getDocument({
          data,
          cMapUrl: "/pdfjs/cmaps/",
          cMapPacked: true,
          standardFontDataUrl: "/pdfjs/standard_fonts/",
          wasmUrl: "/pdfjs/wasm/",
          iccUrl: "/pdfjs/iccs/",
          useSystemFonts: false,
          enableXfa: false,
          stopAtErrors: true,
          maxImageSize: 40_000_000,
          canvasMaxAreaInBytes: 16 * 1024 * 1024,
          verbosity: 0,
        });
        loading.onPassword = () => {
          if (!stopped) setDocumentState({ file, attempt, error: "Password-protected PDFs cannot be previewed. Choose an unencrypted PDF." });
          void loading?.destroy().catch(() => undefined);
        };
        timer = setTimeout(() => {
          if (stopped) return;
          setDocumentState({ file, attempt, error: "This preview took too long. Retry the preview or choose a smaller PDF." });
          void loading?.destroy().catch(() => undefined);
        }, 30_000);
        const pdf = await loading.promise;
        clearTimeout(timer);
        if (stopped) return;
        if (!pdf.numPages || pdf.numPages > BACKEND_LIMITS.maxPdfPages) {
          await loading.destroy();
          setDocumentState({ file, attempt, error: `Choose a PDF with 1–${BACKEND_LIMITS.maxPdfPages.toLocaleString()} pages.` });
          return;
        }
        setDocumentState({ file, attempt, pdf, loading });
        onPageCount?.(pdf.numPages);
      } catch {
        if (timer) clearTimeout(timer);
        void loading?.destroy().catch(() => undefined);
        if (!stopped) setDocumentState((previous) => previous?.file === file && previous.attempt === attempt && previous.error
          ? previous : { file, attempt, error: "This PDF could not be previewed. Retry or replace it with a readable, unencrypted PDF." });
      }
    };
    void load();
    return () => {
      stopped = true;
      if (timer) clearTimeout(timer);
      onPageCount?.(undefined);
      void loading?.destroy().catch(() => undefined);
    };
  }, [file, attempt, onPageCount]);

  const state = documentState?.file === file && documentState.attempt === attempt ? documentState : undefined;
  const pdf = state?.pdf;
  const documentTask = state?.loading;
  const pageWindow = previewPageWindow(pdf?.numPages ?? 0, windowChoice?.file === file ? windowChoice.index : 0);

  useEffect(() => {
    if (!pdf) return;
    let stopped = false;
    let nextPage = pageWindow.first;
    const tasks = new Set<RenderTask>();
    const canvases: HTMLCanvasElement[] = [];
    for (let number = pageWindow.first; number <= pageWindow.last; number++) {
      const canvas = canvasRefs.current.get(number);
      if (canvas) canvases.push(canvas);
    }
    const setPage = (number: number, page: PageState) => {
      if (stopped) return;
      setWindowState((current) => ({ pdf, index: pageWindow.index, pages: { ...(current?.pdf === pdf && current.index === pageWindow.index ? current.pages : {}), [number]: page } }));
    };
    const timer = setTimeout(() => {
      if (stopped) return;
      stopped = true;
      for (const task of tasks) task.cancel();
      setDocumentState({ file, attempt, error: "Some pages took too long to preview. Retry or choose a smaller PDF." });
      void documentTask?.destroy().catch(() => undefined);
    }, 30_000);

    const renderLane = async () => {
      while (!stopped && nextPage <= pageWindow.last) {
        const number = nextPage++;
        let task: RenderTask | undefined;
        let page: PDFPageProxy | undefined;
        try {
          page = await pdf.getPage(number);
          if (stopped) return;
          const viewport = page.getViewport({ scale: 1 });
          if (page.userUnit !== 1 || !Number.isFinite(viewport.width) || !Number.isFinite(viewport.height) || Math.min(viewport.width, viewport.height) < 1 || Math.max(viewport.width, viewport.height) > 14_400) throw new Error("geometry");
          const size = { width: viewport.width, height: viewport.height };
          const canvas = canvasRefs.current.get(number);
          if (!canvas) return;
          const scale = Math.min(320 / size.width, 420 / size.height, 2);
          const thumbnailViewport = page.getViewport({ scale });
          canvas.width = Math.max(1, Math.ceil(thumbnailViewport.width));
          canvas.height = Math.max(1, Math.ceil(thumbnailViewport.height));
          setPage(number, size);
          task = page.render({ canvas, viewport: thumbnailViewport, annotationMode: 0, background: "rgb(255,255,255)" });
          tasks.add(task);
          await task.promise;
          tasks.delete(task);
          if (!stopped) {
            setPage(number, { ...size, ready: true });
          }
        } catch {
          if (task) tasks.delete(task);
          if (!stopped) setPage(number, { width: 210, height: 297, error: "Page preview unavailable" });
        } finally {
          page?.cleanup();
        }
      }
    };
    void Promise.all([renderLane(), renderLane()]).finally(() => clearTimeout(timer));
    return () => {
      stopped = true;
      clearTimeout(timer);
      for (const task of tasks) task.cancel();
      for (const canvas of canvases) { canvas.width = 0; canvas.height = 0; }
    };
  }, [pdf, documentTask, file, attempt, pageWindow.first, pageWindow.last, pageWindow.index]);

  useEffect(() => {
    if (!image) return;
    let stopped = false;
    let url: string | undefined;
    const decode = async () => {
      try {
        if (image.size <= 0 || image.size > BACKEND_LIMITS.maxFileBytes) throw new Error("image-limit");
        const header = watermarkImageDimensions(new Uint8Array(await image.slice(0, 1024 * 1024).arrayBuffer()));
        if (!header || stopped) throw new Error("image-type");
        const bitmap = await createImageBitmap(image.slice(0, image.size, header.mime), { imageOrientation: "from-image" });
        let blob: Blob | null = null;
        const width = bitmap.width, height = bitmap.height;
        try {
          if (stopped) return;
          if (width * height > 16_000_000) throw new Error("image-pixels");
          const canvas = document.createElement("canvas");
          try {
            const ratio = Math.min(1, 1200 / width, 1200 / height);
            canvas.width = Math.max(1, Math.ceil(width * ratio));
            canvas.height = Math.max(1, Math.ceil(height * ratio));
            const context = canvas.getContext("2d");
            if (!context) throw new Error("image-canvas");
            context.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
            blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, "image/png"));
          } finally { canvas.width = 0; canvas.height = 0; }
        } finally { bitmap.close(); }
        if (stopped) return;
        if (!blob) throw new Error("image-encoding");
        url = URL.createObjectURL(blob);
        setImageState({ file: image, url, width, height });
      } catch {
        if (!stopped) setImageState({ file: image, width: 0, height: 0, error: "This image could not be previewed. Use a valid PNG, JPG or WEBP up to 16 million pixels." });
      }
    };
    void decode();
    return () => { stopped = true; if (url) URL.revokeObjectURL(url); };
  }, [image]);

  const currentImage = imageState?.file === image ? imageState : undefined;
  const textSize = options.kind === "text" ? watermarkTextSize(options.text, METRICS) : undefined;
  const markSize = options.kind === "image" && currentImage?.url ? currentImage : textSize;
  const validOptions = !validateWatermarkOptions(options, image, BACKEND_LIMITS.maxFileBytes);

  if (state?.error) return <section ref={previewRef} tabIndex={-1} className="watermark-preview watermark-preview-error" aria-label="PDF preview"><p role="alert">{state.error}</p><button type="button" onClick={() => { previewRef.current?.focus(); setAttempt((value) => value + 1); }}>Retry preview</button><p>Your selected file and watermark settings are unchanged.</p></section>;
  if (!pdf) return <section ref={previewRef} tabIndex={-1} className="watermark-preview watermark-preview-loading" aria-label="PDF preview" role="status"><p>Preparing your page previews locally…</p></section>;

  return <section ref={previewRef} tabIndex={-1} className="watermark-preview" aria-label="PDF page previews">
    <div className="watermark-preview-heading"><h2>{pdf.numPages} {pdf.numPages === 1 ? "page" : "pages"}</h2><p>Placement preview · original PDF quality is kept on export</p></div>
    {currentImage?.error && options.kind === "image" ? <p role="alert" className="watermark-preview-error">{currentImage.error}</p> : null}
    <div className="watermark-thumbnail-grid">
      {pageWindow.pages.map((number) => {
        const page = windowState?.pdf === pdf && windowState.index === pageWindow.index ? windowState.pages[number] : undefined;
        const selected = !pageError && selectedPreviewPage(pages, number, pdf.numPages);
        const placement = page?.ready && markSize && validOptions && selected ? watermarkPlacement(markSize, page, numericWatermarkPlacement(options)) : undefined;
        return <figure className="watermark-thumbnail" key={number}>
          <div className="watermark-thumbnail-page" style={{ aspectRatio: page ? `${page.width} / ${page.height}` : "210 / 297" }}>
            <canvas ref={(canvas) => { if (canvas) canvasRefs.current.set(number, canvas); else canvasRefs.current.delete(number); }} aria-label={`Original PDF page ${number}`} role="img" />
            {placement && page && markSize ? <svg className="preview-watermark" aria-hidden="true" viewBox={`0 0 ${page.width} ${page.height}`}>
              <g transform={`matrix(${placement.matrix.join(" ")})`} opacity={Number(options.opacity)}>
                {options.kind === "image" && currentImage?.url ? <image href={currentImage.url} width={markSize.width} height={markSize.height} /> : <text x="0" y={HELVETICA_ASCENDER * 100} fontSize="100" fontFamily="Arial, Helvetica, sans-serif" fill="#000" textLength={markSize.width - 0.01} lengthAdjust="spacingAndGlyphs">{options.text}</text>}
              </g>
            </svg> : null}
          </div>
          <figcaption className="watermark-thumbnail-label"><span>Page {number}</span><small>{page?.error ?? (!page?.ready ? "Loading preview…" : !selected ? "Not selected" : placement ? "Watermark applied" : "Set watermark options")}</small></figcaption>
        </figure>;
      })}
    </div>
    {pageWindow.windows > 1 ? <nav className="watermark-preview-pagination" aria-label="Preview pages"><button type="button" disabled={pageWindow.index === 0} onClick={() => setWindowChoice({ file, index: pageWindow.index - 1 })}>Previous pages</button><span aria-live="polite">Pages {pageWindow.first}–{pageWindow.last} of {pdf.numPages}</span><button type="button" disabled={pageWindow.index >= pageWindow.windows - 1} onClick={() => setWindowChoice({ file, index: pageWindow.index + 1 })}>Next pages</button></nav> : null}
  </section>;
}
