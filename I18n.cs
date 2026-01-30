using System;
using System.Text;
using System.Runtime.InteropServices;
using Microsoft.Win32.SafeHandles;

namespace I18nTokenEngine
{
    public class I18n : IDisposable
    {
        private sealed class EngineHandle : SafeHandleZeroOrMinusOneIsInvalid
        {
            public EngineHandle() : base(true)
            {
                SetHandle(i18n_new());
            }

            protected override bool ReleaseHandle()
            {
                if (!IsInvalid)
                {
                    i18n_free(handle);
                    SetHandle(IntPtr.Zero);
                }
                return true;
            }
        }

        private EngineHandle _handle;

        public enum MetaPluralRule : byte
        {
            Default = 0,
            Slavic = 1,
            Arabic = 2
        }

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
        private static extern int i18n_translate_plural(IntPtr ptr, byte[] token, int count, IntPtr args, int argsLen, byte[] outBuf, int bufSize);

        [DllImport(DllName, CallingConvention = CallingConvention.Cdecl)]
        private static extern int i18n_export_binary(IntPtr ptr, byte[] path);

        [DllImport(DllName, CallingConvention = CallingConvention.Cdecl)]
        private static extern int i18n_last_error_copy(IntPtr ptr, byte[] buf, int size);

        [DllImport(DllName, CallingConvention = CallingConvention.Cdecl)]
        private static extern int i18n_get_meta_locale_copy(IntPtr ptr, byte[] buf, int size);

        [DllImport(DllName, CallingConvention = CallingConvention.Cdecl)]
        private static extern int i18n_get_meta_fallback_copy(IntPtr ptr, byte[] buf, int size);

        [DllImport(DllName, CallingConvention = CallingConvention.Cdecl)]
        private static extern int i18n_get_meta_note_copy(IntPtr ptr, byte[] buf, int size);

        [DllImport(DllName, CallingConvention = CallingConvention.Cdecl)]
        private static extern int i18n_get_meta_plural_rule(IntPtr ptr);

        public I18n()
        {
            _handle = new EngineHandle();
            if (_handle.IsInvalid) throw new InvalidOperationException("Failed to initialize I18n engine.");
        }

        public void LoadFile(string path, bool strict = true)
        {
            var data = Encoding.UTF8.GetBytes(path);
            var cstr = new byte[data.Length + 1];
            Array.Copy(data, cstr, data.Length);

            Execute(handle =>
            {
                if (i18n_load_txt_file(handle, cstr, strict ? 1 : 0) != 0)
                {
                    throw new InvalidOperationException($"I18n Load Error: {_last_error()}");
                }
            });
        }

        public string Translate(string token, params string[] args)
        {
            var tokenBytes = Encoding.UTF8.GetBytes(token);
            var tokenCStr = new byte[tokenBytes.Length + 1];
            Array.Copy(tokenBytes, tokenCStr, tokenBytes.Length);

            PrepareArgs(args, out var handles, out var argPtrs);
            try
            {
                using var argsRoot = GCHandle.Alloc(argPtrs, GCHandleType.Pinned);
                int len = Execute(handle => i18n_translate(handle, tokenCStr, argsRoot.AddrOfPinnedObject(), args.Length, null, 0));
                if (len < 0) throw new InvalidOperationException($"I18n error: {_last_error()}");

                var buffer = new byte[len + 1];
                Execute(handle => i18n_translate(handle, tokenCStr, argsRoot.AddrOfPinnedObject(), args.Length, buffer, buffer.Length));
                return Encoding.UTF8.GetString(buffer, 0, len);
            }
            finally
            {
                ReleaseHandles(handles);
            }
        }

        public string TranslatePlural(string token, int count, params string[] args)
        {
            var tokenBytes = Encoding.UTF8.GetBytes(token);
            var tokenCStr = new byte[tokenBytes.Length + 1];
            Array.Copy(tokenBytes, tokenCStr, tokenBytes.Length);

            PrepareArgs(args, out var handles, out var argPtrs);
            try
            {
                using var argsRoot = GCHandle.Alloc(argPtrs, GCHandleType.Pinned);
                int len = Execute(handle => i18n_translate_plural(handle, tokenCStr, count, argsRoot.AddrOfPinnedObject(), args.Length, null, 0));
                if (len < 0) throw new InvalidOperationException($"I18n error: {_last_error()}");

                var buffer = new byte[len + 1];
                Execute(handle => i18n_translate_plural(handle, tokenCStr, count, argsRoot.AddrOfPinnedObject(), args.Length, buffer, buffer.Length));
                return Encoding.UTF8.GetString(buffer, 0, len);
            }
            finally
            {
                ReleaseHandles(handles);
            }
        }

        public void ExportBinary(string path)
        {
            var bytes = Encoding.UTF8.GetBytes(path);
            var cstr = new byte[bytes.Length + 1];
            Array.Copy(bytes, cstr, bytes.Length);

            try
            {
                Execute(handle =>
                {
                    if (i18n_export_binary(handle, cstr) != 0)
                    {
                        throw new InvalidOperationException($"Binary export failed: {_last_error()}");
                    }
                });
            }
            catch (InvalidOperationException)
            {
                throw;
            }
        }

        public string GetMetaLocale() => CopyString((handle, buf, size) => i18n_get_meta_locale_copy(handle, buf, size));

        public string GetMetaFallback() => CopyString((handle, buf, size) => i18n_get_meta_fallback_copy(handle, buf, size));

        public string GetMetaNote() => CopyString((handle, buf, size) => i18n_get_meta_note_copy(handle, buf, size));

        public MetaPluralRule GetMetaPluralRule()
        {
            int raw = Execute(handle => i18n_get_meta_plural_rule(handle));
            return Enum.IsDefined(typeof(MetaPluralRule), raw)
                ? (MetaPluralRule)raw
                : MetaPluralRule.Default;
        }

        private string CopyString(Func<IntPtr, byte[], int, int> copyFn)
        {
            int required = Execute(handle => copyFn(handle, null, 0));
            if (required < 0)
            {
                throw new InvalidOperationException($"I18n copy call failed with {required}");
            }
            if (required == 0) return string.Empty;

            var buffer = new byte[required + 1];
            int len = Execute(handle => copyFn(handle, buffer, buffer.Length));
            if (len < 0)
            {
                throw new InvalidOperationException($"I18n copy call failed with {len}");
            }
            if (len == 0) return string.Empty;
            return Encoding.UTF8.GetString(buffer, 0, Math.Min(len, buffer.Length));
        }

        private string _last_error() => CopyString((handle, buf, size) => i18n_last_error_copy(handle, buf, size));

        private void PrepareArgs(string[] args, out GCHandle[] handles, out IntPtr[] pointers)
        {
            handles = new GCHandle[args.Length];
            pointers = new IntPtr[args.Length];
            for (int i = 0; i < args.Length; i++)
            {
                var bytes = Encoding.UTF8.GetBytes(args[i] ?? string.Empty);
                var cstr = new byte[bytes.Length + 1];
                Array.Copy(bytes, cstr, bytes.Length);
                handles[i] = GCHandle.Alloc(cstr, GCHandleType.Pinned);
                pointers[i] = handles[i].AddrOfPinnedObject();
            }
        }

        private static void ReleaseHandles(GCHandle[] handles)
        {
            foreach (var handle in handles)
            {
                if (handle.IsAllocated) handle.Free();
            }
        }

        private T Execute<T>(Func<IntPtr, T> action)
        {
            EnsureHandle();
            bool added = false;
            _handle.DangerousAddRef(ref added);
            try
            {
                return action(_handle.DangerousGetHandle());
            }
            finally
            {
                if (added) _handle.DangerousRelease();
            }
        }

        private void Execute(Action<IntPtr> action)
        {
            Execute(handle =>
            {
                action(handle);
                return 0;
            });
        }

        private void EnsureHandle()
        {
            if (_handle == null || _handle.IsInvalid)
            {
                throw new ObjectDisposedException(nameof(I18n));
            }
        }

        public void Dispose()
        {
            Dispose(true);
            GC.SuppressFinalize(this);
        }

        protected virtual void Dispose(bool disposing)
        {
            if (_handle != null)
            {
                _handle.Dispose();
                _handle = null;
            }
        }

        ~I18n() => Dispose(false);
    }
}
