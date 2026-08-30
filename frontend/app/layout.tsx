import type { Metadata } from "next";
import localFont from "next/font/local";
import "./globals.css";

const geist = localFont({
  src: "./fonts/Geist-Variable.woff2",
  variable: "--font-geist",
  display: "swap",
  style: "normal",
  weight: "100 900",
});

export const metadata: Metadata = {
  applicationName: "PrivCon",
  title: {
    default: "PrivCon",
    template: "%s | PrivCon",
  },
  description:
    "Convert Office documents, PDFs, and images locally on your machine.",
  icons: {
    icon: "/brand/privcon-favicon.png",
    apple: "/brand/privcon-favicon.png",
  },
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={geist.variable}>
      <body>{children}</body>
    </html>
  );
}
