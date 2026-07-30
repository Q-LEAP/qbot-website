/* Exécuté en <head> avant le premier rendu — évite le flash de thème */
(function () {
  var saved = localStorage.getItem('qbot-theme');
  var prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  document.documentElement.setAttribute('data-theme', saved || (prefersDark ? 'dark' : 'light'));
}());
