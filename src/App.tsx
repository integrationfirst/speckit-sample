import { SiteFooter } from "./components/SiteFooter";
import { SiteHeader } from "./components/SiteHeader";

export function App() {
  return (
    <div className="flex min-h-dvh flex-col bg-white text-slate-900">
      <SiteHeader />
      <main className="flex-1">
        <div className="mx-auto max-w-3xl px-4 py-8 sm:px-6 sm:py-12 lg:px-8 lg:py-16">
          <h1 className="text-3xl font-bold break-words sm:text-4xl lg:text-5xl">
            Welcome to speckit-sample
          </h1>
          <p className="mt-4 text-base text-slate-600 sm:text-lg">
            This app is the foundation for upcoming features.
          </p>
        </div>
      </main>
      <SiteFooter />
    </div>
  );
}
