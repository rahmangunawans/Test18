#!/usr/bin/env python3
"""
Test script untuk mengekstrak M3U8 dari DASH URL yang disediakan user
"""

from iqiyi_dash_extractor import extract_m3u8_from_dash_url
import logging

def test_dash_extraction():
    """Test ekstraksi M3U8 dengan DASH URL dari user"""
    
    # DASH URL yang disediakan user
    dash_url = "https://cache.video.iqiyi.com/dash?tvid=3672014441006600&bid=200&ds=1&vid=abe2c4788688b54418ebe6a4119bf1a5&src=01010031010018000000&vt=0&rs=1&uid=0&ori=pcw&ps=0&k_uid=4d8239f8e7e86acec9b8e4892c783a6b&pt=0&d=1&s=&lid=&slid=0&cf=&ct=&authKey=42137e8b905ab43deed845db376fc327&k_tag=1&ost=0&ppt=0&dfp=&prio=%7B%22ff%22%3A%22f4v%22%2C%22code%22%3A2%7D&k_err_retries=0&up=&su=2&applang=en_us&sver=2&X-USER-MODE=&qd_v=2in&tm=1753933550332&k_ft1=2748779069572&k_ft4=1572868&k_ft7=4&k_ft5=16777217&bop=%7B%22version%22%3A%2210.0%22%2C%22dfp%22%3A%22%22%2C%22b_ft1%22%3A0%7D&ut=0&vf=eb938fe2c3514da11e2f2c3ebd1c614b"
    
    print("🎬 Testing DASH URL M3U8 Extraction")
    print("=" * 60)
    print(f"📍 Source URL: https://www.iq.com/play/super-cube-episode-1-11eihk07dr8")
    print(f"🔗 DASH URL: {dash_url[:100]}...")
    print()
    
    # Extract M3U8
    result = extract_m3u8_from_dash_url(dash_url)
    
    print("\n" + "=" * 60)
    print("📊 EXTRACTION RESULTS:")
    print("=" * 60)
    
    if result['success']:
        print("✅ STATUS: SUCCESS")
        print(f"🔄 METHOD: {result['method'].upper()}")
        print(f"📏 M3U8 SIZE: {len(result['m3u8_content']):,} characters")
        print(f"🎞️  SEGMENTS: {result['m3u8_content'].count('#EXTINF:')} video segments")
        
        print("\n📝 M3U8 PREVIEW (first 500 characters):")
        print("-" * 40)
        print(result['m3u8_content'][:500])
        print("-" * 40)
        
        print("\n🔍 M3U8 ANALYSIS:")
        m3u8_lines = result['m3u8_content'].split('\n')
        extinf_count = len([line for line in m3u8_lines if line.startswith('#EXTINF:')])
        ts_count = len([line for line in m3u8_lines if line.endswith('.ts')])
        
        print(f"   • Total lines: {len(m3u8_lines)}")
        print(f"   • EXTINF entries: {extinf_count}")
        print(f"   • TS segment URLs: {ts_count}")
        print(f"   • Target duration: {'Found' if '#EXT-X-TARGETDURATION:' in result['m3u8_content'] else 'Not found'}")
        print(f"   • Playlist type: {'VOD' if '#EXT-X-PLAYLIST-TYPE:VOD' in result['m3u8_content'] else 'Live/Other'}")
        
        # Tampilkan beberapa sample segment URLs
        ts_urls = [line.strip() for line in m3u8_lines if line.strip().endswith('.ts')]
        if ts_urls:
            print(f"\n🎯 SAMPLE SEGMENT URLS (first 3):")
            for i, url in enumerate(ts_urls[:3], 1):
                print(f"   {i}. {url[:80]}...")
        
        print(f"\n🎉 RESULT: M3U8 berhasil diekstrak dan siap untuk streaming!")
        print(f"💡 INFO: M3U8 dapat digunakan langsung dengan HLS.js atau Video.js")
        
    else:
        print("❌ STATUS: FAILED")
        print(f"💥 ERROR: {result['error']}")
        if 'raw_data' in result and result['raw_data']:
            print(f"📄 RAW DATA LENGTH: {len(str(result['raw_data']))} characters")
    
    print("\n" + "=" * 60)
    return result

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_dash_extraction()