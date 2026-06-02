---
hide:
  - navigation
  - toc
---

<section class="mm-hero">
  <div class="mm-hero__copy">
    <p class="mm-eyebrow">Local-first media library</p>
    <h1>Organize your media without giving up control.</h1>
    <p class="mm-lead">
      MM indexes existing folders, imports new photos and videos safely, creates
      thumbnails, and gives you a clean web UI from one lightweight Python package.
    </p>
    <div class="mm-actions">
      <a class="mm-button mm-button--primary" href="https://hspk.github.io/mm/tutorials/getting-started/">Get started</a>
      <a class="mm-button" href="https://github.com/HSPK/mm">View on GitHub</a>
    </div>
  </div>
  <div class="mm-preview" aria-label="Media library preview">
    <div class="mm-preview__bar">
      <span></span><span></span><span></span>
      <strong>Library</strong>
    </div>
    <div class="mm-preview__body">
      <aside>
        <b></b>
        <i class="active"></i>
        <i></i>
        <i class="short"></i>
      </aside>
      <main>
        <div class="mm-preview__toolbar">
          <strong>Summer archive</strong>
          <em>Tags · Camera · Places</em>
        </div>
        <div class="mm-grid">
          <span class="tall"></span><span class="warm"></span><span></span><span class="green"></span>
          <span class="dark"></span><span class="tall green"></span><span class="warm"></span><span></span>
        </div>
      </main>
    </div>
  </div>
</section>

<section class="mm-strip">
  <span>SQLite by default</span>
  <span>PostgreSQL when needed</span>
  <span>No sidecar writes</span>
  <span>Noncommercial license</span>
  <span>CLI + Web UI</span>
</section>

## What MM helps you do

<div class="mm-card-grid">
  <article>
    <h3>Start with your existing folders</h3>
    <p>Point MM at a media folder and build a searchable library without moving everything first.</p>
  </article>
  <article>
    <h3>Import new media safely</h3>
    <p>Copy or move new files into predictable folders with duplicate checks and import plans.</p>
  </article>
  <article>
    <h3>Browse from a web UI</h3>
    <p>Use a responsive gallery with thumbnails, metadata, tags, ratings, and smart albums.</p>
  </article>
  <article>
    <h3>Keep the deployment small</h3>
    <p>Use SQLite for a portable local setup, or register PostgreSQL for a server-backed library.</p>
  </article>
</div>

## Recommended first steps

1. Install the command line app.
2. Create a library for the folder where your media lives.
3. Start the web UI.
4. Import or sync new media when needed.

```bash
pipx install litemm
mm init ~/Photos
mm server
```

Continue with the [Getting Started tutorial](tutorials/getting-started.md).
