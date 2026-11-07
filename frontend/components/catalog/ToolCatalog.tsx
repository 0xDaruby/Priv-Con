"use client";

import { useRef, useState } from "react";
import Link from "next/link";

import { PrivacyShieldCheckIcon, ToolFileIcon } from "@/components/icons/PrivConIcons";
import { TOOLS } from "@/lib/constants";
import { getCatalogGroups } from "@/lib/tool-catalog";
import type { ToolCategoryFilter } from "@/lib/tool-catalog";

export function ToolCatalog() {
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState<ToolCategoryFilter>("all");
  const searchRef = useRef<HTMLInputElement>(null);
  const availableGroups = getCatalogGroups(TOOLS);
  const groups = getCatalogGroups(TOOLS, query, category);
  const resultCount = groups.reduce((count, group) => count + group.tools.length, 0);
  const filtered = query.trim().length > 0 || category !== "all";

  const clearFilters = () => {
    setQuery("");
    setCategory("all");
    searchRef.current?.focus();
  };

  return (
    <section className="tool-catalog" aria-labelledby="catalog-title">
      <header className="catalog-intro">
        <div>
          <h1 id="catalog-title">All tools</h1>
          <p className="catalog-description">Choose what you want to do with your document.</p>
        </div>
        <div className="catalog-privacy">
          <PrivacyShieldCheckIcon />
          <p>Files are processed entirely on this machine.<br />Nothing is uploaded anywhere.</p>
        </div>
      </header>

      <div className="catalog-discovery">
        <div className="catalog-search-field">
          <label htmlFor="tool-search">Find a tool</label>
          <div className="catalog-search-control">
            <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7">
              <circle cx="10.5" cy="10.5" r="6.5" />
              <path d="m15.5 15.5 4.5 4.5" />
            </svg>
            <input
              autoComplete="off"
              id="tool-search"
              ref={searchRef}
              maxLength={128}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search by name or task, like merge or images"
              type="search"
              value={query}
            />
            {query ? (
              <button aria-label="Clear search" onClick={() => { setQuery(""); searchRef.current?.focus(); }} type="button">Clear</button>
            ) : null}
          </div>
        </div>
        <div className="catalog-category-select">
          <label htmlFor="tool-category">Category</label>
          <select id="tool-category" value={category} onChange={(event) => setCategory(event.target.value as ToolCategoryFilter)}>
            <option value="all">All tools ({TOOLS.length})</option>
            {availableGroups.map((group) => <option key={group.id} value={group.id}>{group.label} ({group.tools.length})</option>)}
          </select>
        </div>
        <div className="catalog-filters" role="group" aria-label="Filter tools by category">
          <button aria-pressed={category === "all"} onClick={() => setCategory("all")} type="button">
            All tools <span>{TOOLS.length}</span>
          </button>
          {availableGroups.map((group) => (
            <button aria-pressed={category === group.id} key={group.id} onClick={() => setCategory(group.id)} type="button">
              {group.label} <span>{group.tools.length}</span>
            </button>
          ))}
        </div>
      </div>

      <p aria-atomic="true" className="catalog-result-count" role="status">
        {resultCount} {resultCount === 1 ? "tool" : "tools"} {filtered ? "found" : "available"}
      </p>

      {groups.length ? (
        <div className="catalog-groups">
          {groups.map((group) => (
            <section aria-labelledby={`category-${group.id}`} className="catalog-group" key={group.id}>
              <div className="catalog-group-heading">
                <h2 id={`category-${group.id}`}>{group.label}</h2>
                <p>{group.description}</p>
              </div>
              <ul className="catalog-tool-grid">
                {group.tools.map((tool) => (
                  <li key={tool.id}>
                    <Link className="catalog-tool-link" href={tool.route}>
                      <span aria-hidden="true" className="catalog-tool-icon"><ToolFileIcon name={tool.icon} /></span>
                      <span className="catalog-tool-copy">
                        <strong>{tool.title}</strong>
                        <span>{tool.description}</span>
                        <small>{tool.acceptedFormatLabel}</small>
                      </span>
                      <svg aria-hidden="true" className="catalog-tool-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
                        <path d="M5 12h14m-5-5 5 5-5 5" />
                      </svg>
                    </Link>
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </div>
      ) : (
        <div className="catalog-empty">
          <h2>No tools found</h2>
          <p>Try another name or clear the filters.</p>
          <button className="catalog-clear-filters" onClick={clearFilters} type="button">Clear filters</button>
        </div>
      )}
    </section>
  );
}
