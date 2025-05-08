using System;

public class CheckIrreg
{
    private const int MAXIRREGS = 10;
    private const int MAXIRR = 3;

    private static string[] IrrForms = new string[MAXIRR];
    private static string[] IrrKeys = new string[MAXIRR];
    private static bool init_stor = false;

    public static int try_irregvb(GkWord Gkword)
    {
        GkWord Workword = new GkWord();
        string saveirrform = null;
        string keys = null;
        string fullpreverb;
        int unasp_prev = 0;

        int rval = 0;
        int i;
        string irrform;
        string rawprvb;

        saveirrform = new string(new char[MAXWORDSIZE]);
        keys = new string(new char[LONGSTRING]);
        saveirrform = keys = string.Empty;

        if (!init_stor)
        {
            init_stor = true;
            for (i = 0; i < MAXIRR; i++)
            {
                IrrForms[i] = new string(new char[MAXWORDSIZE]);
                IrrKeys[i] = new string(new char[LONGSTRING]);
            }
        }
        for (i = 0; i < MAXIRR; i++)
        {
            IrrForms[i] = string.Empty;
            IrrKeys[i] = string.Empty;
        }

        Workword = Gkword.Clone();
        rawprvb = Workword.RawPreverb;
        fullpreverb = Workword.Preverb;
        irrform = Workword.Stem;

        Workword.PrvbGstr.MorphFlags = 0;
        fullpreverb = IrrKeys[0] = IrrKeys[1] = IrrKeys[2] = string.Empty;

        if (!string.IsNullOrEmpty(rawprvb))
        {
            if (!IsPreverb(rawprvb, fullpreverb, Workword.PrvbGstr))
            {
                rval = 0;
                goto finish;
            }
            Workword.StemGstr.MorphFlags |= MorphFlags.HAS_PREVERB;
        }

        if (Workword.PrvbGstr.MorphFlags.HasFlag(MorphFlags.APOCOPE))
        {
            if (AndDialect(Workword.Dialect, Dialect.PROSE) > 0)
                goto finish;
        }

        if (!string.IsNullOrEmpty(rawprvb) && !CombPbStem(rawprvb, irrform, Workword.Dialect, Workword.PrvbGstr.MorphFlags))
        {
            rval = 0;
            goto finish;
        }
        Workword.StemGstr.MorphFlags |= Workword.PrvbGstr.MorphFlags;

        if (string.IsNullOrEmpty(rawprvb) || IsCons(irrform[0]) || cur_lang() == Language.LATIN)
        {
            rval = ChckIrrvForm(irrform, IrrKeys[0]);
            if (rval)
            {
                rval = ChckIrrLemms(Workword, irrform, IrrKeys[0]);
                goto finish;
            }
        }

        if (!IsVowel(irrform[0]))
            goto finish;

        if (GetBreath(irrform) != Breath.NOBREATH)
        {
            rval = ChckIrrvForm(irrform, IrrKeys[0]);
            if (rval)
                IrrForms[0] = irrform;
            else
                IrrForms[0] = string.Empty;
        }

        saveirrform = irrform;

        if ((cur_lang() != Language.LATIN && (!IsAsp(rawprvb[^1]) || MfiPrvb(rawprvb))) && GetBreath(irrform) == Breath.NOBREATH)
        {
            AddBreath(ref irrform, Breath.SMOOTHBR);
            if (Workword.StemGstr.MorphFlags.HasFlag(MorphFlags.UNASP_PREVERB))
            {
                unasp_prev = 1;
                Workword.StemGstr.MorphFlags &= ~MorphFlags.UNASP_PREVERB;
            }

            rval += ChckIrrvForm(irrform, IrrKeys[0]);

            if (unasp_prev != 0)
            {
                unasp_prev = 0;
                Workword.StemGstr.MorphFlags |= MorphFlags.UNASP_PREVERB;
            }
            if (rval)
                IrrForms[0] = irrform;
            else
                IrrForms[0] = string.Empty;
        }

        irrform = saveirrform;

        if (cur_lang() != Language.LATIN && cur_lang() != Language.ITALIAN && GetBreath(irrform) == Breath.NOBREATH && (!IsVowel(irrform[0]) || !string.IsNullOrEmpty(rawprvb)))
        {
            AddBreath(ref irrform, Breath.ROUGHBR);
            rval = ChckIrrvForm(irrform, IrrKeys[1]);

            if (rval)
                IrrForms[rval] = irrform;
            else
                IrrForms[1] = string.Empty;
        }
        irrform = saveirrform;

        rval = 0;

        if (!string.IsNullOrEmpty(IrrForms[1]))
            rval += ChckIrrLemms(Workword, IrrForms[1], IrrKeys[1]);

        rval += ChckIrrLemms(Workword, IrrForms[0], IrrKeys[0]);

    finish:
        saveirrform = keys = fullpreverb = null;

        if (rval)
            Gkword.CopyAnalysis(Workword);
        return rval;
    }

    public static int ChckIrrLemms(GkWord Gkword, string irrform, string irrkey)
    {
        string sp;
        string stemkeys = new string(new char[LONGSTRING]);
        string curlemma = new string(new char[LONGSTRING]);
        string tmpword = new string(new char[LONGSTRING]);
        GkWord TmpGkword;
        int rval = 0;
        int curval = 0;

        while (NextKey(ref irrkey, ref curlemma))
        {
            sp = curlemma;
            TmpGkword = Gkword.Clone();

            sp = ParseField(sp, ref tmpword, ':');
            if (!string.IsNullOrEmpty(tmpword))
            {
                irrform = tmpword;
            }
            else
            {
                irrform = Gkword.Stem;
                StripAcc(ref irrform);
                StripQuant(ref irrform);
                StripDiaer(ref irrform);
            }
            sp = ParseField(sp, ref TmpGkword.Lemma, ':');
            sp = ParseField(sp, ref stemkeys, ' ');
            SubChar(ref stemkeys, ':', ' ');

            curval += CheckIrregForm(TmpGkword, irrform, stemkeys);

            if (curval != 0)
            {
                Gkword.CopyAnalysis(TmpGkword);
            }
            rval += curval;
        }
        return rval;
    }

    public static int CheckIrregForm(GkWord Gkword, string stem, string stemkeys)
    {
        GkWord Forms = null;
        GkWord StemForms;
        GkString Gstr;
        string prevb = Gkword.Preverb;
        string pbptr;
        int rval = 0;

        StemForms = Gkword.Clone();
        StemForms.Stem = stem;

        if (!string.IsNullOrEmpty(prevb))
        {
            pbptr = IsSubstring(stemkeys, "pb:");
            if (pbptr == null)
            {
                stemkeys += " pb:" + prevb;
            }
            else if (string.Compare(pbptr.Substring(3), prevb, StringComparison.Ordinal) != 0)
                return 0;
        }

        Forms = GenIrregForm(StemForms, stemkeys, 0);

        Gstr.MorphFlags = Gkword.MorphFlags;
        if (Forms != null)
        {
            rval = CheckGenWords(Gkword, Forms);
            FreeGkString(Forms);
        }
        Gkword.MorphFlags = Gstr.MorphFlags;
        return rval;
    }

    public static int ChckIrrvForm(string form, string keys)
    {
        string tmpform = new string(new char[MAXWORDSIZE]);
        int rval;

        rval = ChckIrrVerb(form, keys);
        return rval;
    }

    public static bool MfiPrvb(string rawprvb)
    {
        int slen = rawprvb.Length;

        if (rawprvb[slen - 1] == 'f' && rawprvb[slen - 2] == 'm') return true;
        return false;
    }
}
