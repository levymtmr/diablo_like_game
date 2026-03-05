# Diablo-like 2D Prototype (pygame)

Prototipo inicial de ARPG 2D feito com Python + pygame.

## Requisitos

- Python 3.10+
- `pip install -r requirements.txt`

## Como executar

```bash
python main.py
```

## Estrutura do projeto

```text
my_diablo_game/
  main.py
  requirements.txt
  README.md
  game/
    __init__.py
    animation.py
    combat_mixin.py
    inventory.py
    inventory_shop_mixin.py
    render_mixin.py
    settings.py
    entities.py
    world.py
    game.py
```

## Responsabilidades dos modulos

- `main.py`: ponto de entrada da aplicacao.
- `game/animation.py`: carregamento de spritesheet e controle de animacoes.
- `game/inventory.py`: modelos de equipamentos e logica de grade/slots.
- `game/combat_mixin.py`: combate, projeteis, spells, wave e update de entidades.
- `game/inventory_shop_mixin.py`: drag-and-drop do inventario e compra/venda da loja.
- `game/render_mixin.py`: renderizacao do mundo, UI, inventario, loja e overlays.
- `game/settings.py`: constantes do jogo (tela, tiles, cores, FPS).
- `game/entities.py`: modelos de entidades (`Entity`, `Player`, `Enemy`).
- `game/world.py`: geracao do mapa e checagem de colisao com tiles bloqueados.
- `game/game.py`: orquestracao principal (init, selecao de classe e roteamento de eventos).

## Animacoes integradas

- Player: `soldier` com `idle`, `walk`, `attack1`, `attack2`, `attack3`, `hurt`, `death`.
- Inimigos: `orc` com `idle`, `walk`, `attack1`, `attack2`, `hurt`, `death`.
- Cenario com tiles do pack `dark_fantasy_terrain_pack` (chao e props de obstaculo).

## Classes e armas

- Classes jogaveis:
- `Guerreiro`: inicia com espada default (ataque melee).
- `Mago`: inicia com spell default (ataque magico).
- `Arqueiro`: inicia com arco default (ataque a distancia).
- Novas swords e spells entram como itens de arma, podem dropar dos inimigos e aparecer na loja.
- Spells implementadas:
- `lighting_spell`: projétil rapido de raio.
- `meteor_spell`: projétil lento com dano em area ao impacto.
- `twister_spell`: projétil com perfuração limitada.
- `field_spell`: explosao ao redor do personagem.
- Animacoes de magia em `assets/animation_spells` aplicadas na conjuracao e no impacto das spells do mago.

## Inventario e equipamentos

- Inventario em grade (estilo ARPG) com organizacao por arrastar/soltar.
- Slots de equipamento: `arma`, `capacete`, `capa`, `cinto`, `botas`.
- Equipamentos dropam dos inimigos e podem ser equipados para alterar atributos.
- Drops no chao: ouro, frascos de vida/mana e equipamentos.
- O mapa possui uma base segura no centro; os inimigos so aparecem quando o player sai da base.
- Sistema de waves: ao limpar uma wave, o player retorna automaticamente para a base.
- Loja na base entre waves para comprar e vender equipamentos.

## Controles

- `1 / 2 / 3` (na tela inicial): escolher classe
- `W A S D` ou setas: mover
- `Clique esquerdo`: atacar com a arma equipada
- `1`: usar frasco vermelho (vida)
- `2`: usar frasco azul (mana)
- `I`: abrir/fechar inventario
- `Mouse no inventario`: arrastar/soltar itens e equipar nos slots
- `B`: abrir/fechar loja (somente na base, entre waves)
- `Clique direito` em item do inventario enquanto loja e inventario estao abertos: vender item
- `TAB`: abrir/fechar mapa grande (overlay)
- `ESC`: sair
- 

<img width="1593" height="899" alt="image" src="https://github.com/user-attachments/assets/80a4505b-21dd-452f-a792-dc93a59b20a2" />

