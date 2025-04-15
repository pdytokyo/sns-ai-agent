"""
subtitle_templates.py - テロップスタイルテンプレートの定義
"""

SUBTITLE_TEMPLATES = [
    {
        "id": "default",
        "name": "標準",
        "font": "Arial",
        "font_size": 24,
        "color": "white",
        "bg_color": "rgba(0, 0, 0, 0.5)",
        "position": "bottom",
        "preview_img": "/static/img/subtitle_templates/default.png",
        "css": """
            font-family: Arial;
            font-size: 24px;
            color: white;
            background-color: rgba(0, 0, 0, 0.5);
            padding: 5px 10px;
            border-radius: 5px;
        """
    },
    {
        "id": "pop",
        "name": "ポップ",
        "font": "Comic Sans MS",
        "font_size": 28,
        "color": "yellow",
        "bg_color": "rgba(0, 0, 150, 0.7)",
        "position": "bottom",
        "preview_img": "/static/img/subtitle_templates/pop.png",
        "css": """
            font-family: 'Comic Sans MS', cursive;
            font-size: 28px;
            color: yellow;
            background-color: rgba(0, 0, 150, 0.7);
            padding: 8px 12px;
            border-radius: 10px;
            font-weight: bold;
        """
    },
    {
        "id": "minimal",
        "name": "ミニマル",
        "font": "Helvetica",
        "font_size": 20,
        "color": "white",
        "bg_color": "transparent",
        "position": "bottom",
        "preview_img": "/static/img/subtitle_templates/minimal.png",
        "css": """
            font-family: Helvetica, sans-serif;
            font-size: 20px;
            color: white;
            background-color: transparent;
            text-shadow: 2px 2px 2px rgba(0, 0, 0, 0.8);
            padding: 5px;
        """
    },
    {
        "id": "stylish",
        "name": "スタイリッシュ",
        "font": "Georgia",
        "font_size": 26,
        "color": "#e0e0e0",
        "bg_color": "rgba(40, 40, 40, 0.9)",
        "position": "bottom",
        "preview_img": "/static/img/subtitle_templates/stylish.png",
        "css": """
            font-family: Georgia, serif;
            font-size: 26px;
            color: #e0e0e0;
            background-color: rgba(40, 40, 40, 0.9);
            padding: 6px 12px;
            border-left: 3px solid #0d6efd;
        """
    },
    {
        "id": "bold",
        "name": "ボールド",
        "font": "Impact",
        "font_size": 30,
        "color": "white",
        "bg_color": "rgba(220, 53, 69, 0.8)",
        "position": "bottom",
        "preview_img": "/static/img/subtitle_templates/bold.png",
        "css": """
            font-family: Impact, sans-serif;
            font-size: 30px;
            color: white;
            background-color: rgba(220, 53, 69, 0.8);
            padding: 5px 10px;
            font-weight: bold;
            letter-spacing: 1px;
        """
    }
]

def get_template_by_id(template_id):
    """
    テンプレートIDからテンプレート情報を取得する
    """
    for template in SUBTITLE_TEMPLATES:
        if template["id"] == template_id:
            return template
    return SUBTITLE_TEMPLATES[0]  # デフォルトテンプレートを返す
