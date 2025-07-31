function alternarTema() {
    const html = document.documentElement;
    const temaAtual = html.getAttribute('data-bs-theme');
    const novoTema = temaAtual === 'dark' ? 'light' : 'dark';
    html.setAttribute('data-bs-theme', novoTema);
    localStorage.setItem('tema', novoTema);
}

// Mantém o tema salvo ao recarregar
window.onload = () => {
    const temaSalvo = localStorage.getItem('tema') || 'light';
    document.documentElement.setAttribute('data-bs-theme', temaSalvo);
};
