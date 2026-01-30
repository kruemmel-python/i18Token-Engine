using System;
using System.Text;
using System.Runtime.InteropServices;

namespace I18nTokenEngine
{
    public class I18n : IDisposable
    {
        private IntPtr _handle;
        private const string DllName = "i18n_engine";

        // --- Native Imports ---

        [DllImport(DllName, CallingConvention = CallingConvention.Cdecl)]
        private static extern IntPtr i18n_new();

        [DllImport(DllName, CallingConvention = CallingConvention.Cdecl)]
        private static extern void i18n_free(IntPtr ptr);

        [DllImport(DllName, CallingConvention = CallingConvention.Cdecl)]
        private static extern int i18n_load_txt_file(IntPtr ptr, byte[] path, int strict);

        [DllImport(DllName, CallingConvention = CallingConvention.Cdecl)]
        private static extern int i18n_translate(IntPtr ptr, byte[] token, IntPtr args, int argsLen, byte[] outBuf, int bufSize);

        [DllImport(DllName, CallingConvention = CallingConvention.Cdecl)]
        private static extern int i18n_last_error_copy(IntPtr ptr, byte[] buf, int size);

        // --- Public API ---

        public I18n()
        {
            _handle = i18n_new();
            if (_handle == IntPtr.Zero) throw new InvalidOperationException("Failed to initialize I18n engine.");
        }

        public void LoadFile(string path, bool strict = true)
        {
            // UTF-8 Encoding + Null-Terminator
            var pathBytes = Encoding.UTF8.GetBytes(path);
            var pathCStr = new byte[pathBytes.Length + 1];
            Array.Copy(pathBytes, pathCStr, pathBytes.Length);

            if (i18n_load_txt_file(_handle, pathCStr, strict ? 1 : 0) != 0)
            {
                throw new Exception($"I18n Load Error: {GetLastError()}");
            }
        }

        public string Translate(string token, params string[] args)
        {
            // Token zu UTF-8 C-String
            var tokenBytes = Encoding.UTF8.GetBytes(token);
            var tokenCStr = new byte[tokenBytes.Length + 1];
            Array.Copy(tokenBytes, tokenCStr, tokenBytes.Length);

            // Argumente manuell marshalen (const char**)
            IntPtr[] argPtrs = new IntPtr[args.Length];
            GCHandle[] handles = new GCHandle[args.Length];
            
            try
            {
                for (int i = 0; i < args.Length; i++)
                {
                    var bytes = Encoding.UTF8.GetBytes(args[i] ?? "");
                    var cstr = new byte[bytes.Length + 1];
                    Array.Copy(bytes, cstr, bytes.Length);
                    
                    handles[i] = GCHandle.Alloc(cstr, GCHandleType.Pinned);
                    argPtrs[i] = handles[i].AddrOfPinnedObject();
                }

                GCHandle argsRoot = GCHandle.Alloc(argPtrs, GCHandleType.Pinned);
                try
                {
                    // 1. Länge ermitteln (Dry Run)
                    int len = i18n_translate(_handle, tokenCStr, argsRoot.AddrOfPinnedObject(), args.Length, null, 0);
                    
                    // 2. Übersetzen
                    var buf = new byte[len + 1];
                    i18n_translate(_handle, tokenCStr, argsRoot.AddrOfPinnedObject(), args.Length, buf, buf.Length);
                    
                    return Encoding.UTF8.GetString(buf, 0, len);
                }
                finally
                {
                    argsRoot.Free();
                }
            }
            finally
            {
                foreach (var h in handles) if (h.IsAllocated) h.Free();
            }
        }

        private string GetLastError()
        {
            var buf = new byte[1024];
            int len = i18n_last_error_copy(_handle, buf, buf.Length);
            return Encoding.UTF8.GetString(buf, 0, len);
        }

        public void Dispose()
        {
            if (_handle != IntPtr.Zero)
            {
                i18n_free(_handle);
                _handle = IntPtr.Zero;
            }
            GC.SuppressFinalize(this);
        }

        ~I18n() => Dispose();
    }
}