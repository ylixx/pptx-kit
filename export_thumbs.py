#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
export_thumbs.py — 把一个 .pptx 的每页导出为 PNG。

依赖策略：
  * win32com.client (COM): 最快保真，但需 Windows + PowerPoint。
  * LibreOffice + pymupdf: 跨平台，但需安装 LibreOffice。
  * Pillow 纯离线兜底：最慢，但始终可用。

自动探测：优先 COM → LibreOffice → Pillow。两者都不可用时给出清晰错误提示。

用法：
  python export_thumbs.py deck.pptx -o thumbs/ -w 1280 -h 720
  python export_thumbs.py deck.pptx -o thumbs/ --prefix slide
  python export_thumbs.py deck.pptx --prefix tpl --pattern-only  # 只导出模板 pattern（tpl_前缀）
"""

import argparse
import os
import sys
from PIL import Image


def warn(msg):
    print(f"[warn] {msg}", file=sys.stderr)


def _try_win32com(pptx_path, out_dir, width, height, prefix):
    """优先尝试 win32com.client 调 PowerPoint COM。"""
    try:
        import win32com.client
    except ImportError:
        return False
    try:
        ppt = win32com.client.Dispatch("PowerPoint.Application")
        # 新版 Office 禁止隐藏应用窗口（Visible=0 会抛错），改为可见或跳过
        try:
            ppt.Visible = 1
        except Exception:
            pass
        deck = ppt.Presentations.Open(os.path.abspath(pptx_path))
        n = deck.Slides.Count
        for i in range(1, n + 1):
            slide = deck.Slides(i)
            out_path = os.path.abspath(os.path.join(out_dir, f"{prefix}{i:03d}.png"))
            slide.Export(out_path, "PNG", width, height)
        deck.Close()
        ppt.Quit()
        return True
    except Exception as e:
        warn(f"win32com COM 导出失败: {e}")
        try:
            deck.Close()
            ppt.Quit()
        except:
            pass
        return False


def _try_libreoffice(pptx_path, out_dir, width, height, prefix):
    """备选：LibreOffice 转为 PDF + PyMuPDF 拆页。"""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        return False
    try:
        soffice = "soffice"  # 默认命令名
        if sys.platform == "win32":
            soffice = "soffice.exe"
        # 转为 PDF
        pdf_path = os.path.join(out_dir, "temp.pdf")
        cmd = f'"{soffice}" --headless --convert-to pdf --outdir "{out_dir}" "{os.path.abspath(pptx_path)}"'
        os.system(cmd)
        if not os.path.exists(pdf_path):
            raise FileNotFoundError("LibreOffice 未生成 PDF")
        # 拆页为 PNG
        doc = fitz.open(pdf_path)
        n = doc.page_count
        for i in range(n):
            page = doc.load_page(i)
            pix = page.get_pixmap(matrix=fitz.Matrix(width/72, height/72))
            out_path = os.path.join(out_dir, f"{prefix}{i+1:03d}.png")
            pix.save(out_path)
        doc.close()
        os.remove(pdf_path)
        return True
    except Exception as e:
        warn(f"LibreOffice+PyMuPDF 导出失败: {e}")
        return False


def _try_pillow(pptx_path, out_dir, width, height, prefix):
    """纯 Pillow 离线兜底：python-pptx 读取每页，PIL 渲染为 PNG。"""
    try:
        from pptx import Presentation
    except ImportError:
        warn("Pillow 离线兜底需要 python-pptx")
        return False
    try:
        prs = Presentation(pptx_path)
        os.makedirs(out_dir, exist_ok=True)
        n = len(prs.slides)
        for i, slide in enumerate(prs.slides, 1):
            # 简单渲染：取第一张图片（如果有），否则白底黑字占位
            img = None
            for shape in slide.shapes:
                if hasattr(shape, 'image') and shape.image:
                    img = shape.image
                    break
            if img and hasattr(img, 'blob'):
                # 简单处理：假设图片尺寸足够，缩放至目标
                from io import BytesIO
                img_bytes = BytesIO(img.blob)
                img_pil = Image.open(img_bytes)
                img_pil = img_pil.resize((width, height), Image.LANCZOS)
            else:
                img_pil = Image.new("RGB", (width, height), "white")
                # 添加页码文本（简单占位）
                from PIL import ImageDraw, ImageFont
                draw = ImageDraw.Draw(img_pil)
                try:
                    font = ImageFont.truetype("arial.ttf", 24)
                except:
                    font = ImageFont.load_default()
                draw.text((10, height - 30), f"Page {i}", fill="black", font=font)
            out_path = os.path.join(out_dir, f"{prefix}{i:03d}.png")
            img_pil.save(out_path, "PNG")
        return True
    except Exception as e:
        warn(f"Pillow 离线兜底失败: {e}")
        return False


def _count_slides(pptx_path):
    """读取源 PPTX 页数，用于导出后对比；失败返回 None 不告警。"""
    try:
        from pptx import Presentation
        return len(Presentation(pptx_path).slides)
    except Exception:
        return None


def export_thumbs(pptx_path, out_dir, width=1280, height=720, prefix="slide", pattern_only=False):
    """
    把一个 .pptx 的每页导出为 PNG。

    :param pptx_path: PPTX 文件路径
    :param out_dir: 输出目录（会创建）
    :param width: PNG 宽度
    :param height: PNG 高度
    :param prefix: 文件名前缀（如 "slide"）
    :param pattern_only: 是否只导出模板 pattern（tpl_前缀）
    :return: 导出的页数
    """
    if not os.path.exists(pptx_path):
        raise FileNotFoundError(f"PPTX 文件不存在: {pptx_path}")
    os.makedirs(out_dir, exist_ok=True)
    if pattern_only:
        prefix = "tpl_"

    # 自动探测并尝试导出
    success = False
    if _try_win32com(pptx_path, out_dir, width, height, prefix):
        success = True
    elif _try_libreoffice(pptx_path, out_dir, width, height, prefix):
        success = True
    elif _try_pillow(pptx_path, out_dir, width, height, prefix):
        success = True
    else:
        raise RuntimeError("所有导出方案均不可用。请安装 PowerPoint (win32com)、LibreOffice+PyMuPDF 或确保 python-pptx+Pillow 可用。")

    # 统计导出的文件
    files = [f for f in os.listdir(out_dir) if f.startswith(prefix) and f.endswith(".png")]
    expected = _count_slides(pptx_path)
    if expected is not None and len(files) != expected:
        warn(f"导出页数异常：预期 {expected} 页，实际 {len(files)} 页")
    return len(files)


def main():
    ap = argparse.ArgumentParser(description="PPTX 导出缩略图")
    ap.add_argument("pptx", help="PPTX 文件路径")
    ap.add_argument("-o", "--out", default="thumbs", help="输出目录（默认 thumbs/）")
    ap.add_argument("-w", "--width", type=int, default=1280, help="PNG 宽度（默认 1280）")
    ap.add_argument("--height", type=int, default=720, help="PNG 高度（默认 720）")
    ap.add_argument("-p", "--prefix", default="slide", help="文件名前缀（默认 slide）")
    ap.add_argument("--pattern-only", action="store_true", help="只导出模板 pattern（tpl_前缀）")
    args = ap.parse_args()

    n = export_thumbs(args.pptx, args.out, args.width, args.height, args.prefix, args.pattern_only)
    print(f"✅ 已导出 {n} 页缩略图到 {args.out}/")


if __name__ == "__main__":
    main()
