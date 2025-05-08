using System;

public class CheckCrasis
{
    private const int MAXCRASIS = 12;
    private const int MAXWORDSIZE = 256;
    private const int LONGSTRING = 1024;

    private struct PreciseCrasis
    {
        public string Crasis;
        public string CurString;
        public int Gender;
        public int Case;
        public int Number;
        public Dialect PossDial;
    }

    private struct PossCrasis
    {
        public string MungedWord;
        public string WordStart;
        public string PreWord;
        public Dialect PossDial;
    }

    private static PreciseCrasis[] CrasTab = new PreciseCrasis[]
    {
        new PreciseCrasis { Crasis = "o(", CurString = "ai(", Gender = FEMININE, Case = NOMINATIVE, Number = PLURAL, PossDial = 0 },
        new PreciseCrasis { Crasis = "o(", CurString = "oi(", Gender = MASCULINE, Case = NOMINATIVE, Number = PLURAL, PossDial = 0 },
        new PreciseCrasis { Crasis = "o(", CurString = "o(", Gender = MASCULINE, Case = NOMINATIVE, Number = SINGULAR, PossDial = 0 },
        new PreciseCrasis { Crasis = "o(", CurString = "h(", Gender = FEMININE, Case = NOMINATIVE, Number = SINGULAR, PossDial = 0 },
        new PreciseCrasis { Crasis = "to/", CurString = "to/", Gender = NEUTER, Case = NOMINATIVE, Number = SINGULAR, PossDial = 0 },
        new PreciseCrasis { Crasis = "to/", CurString = "to/", Gender = NEUTER, Case = VOCATIVE, Number = SINGULAR, PossDial = 0 },
        new PreciseCrasis { Crasis = "to/", CurString = "to/", Gender = NEUTER, Case = ACCUSATIVE, Number = SINGULAR, PossDial = 0 },
        new PreciseCrasis { Crasis = "to/", CurString = "ta/", Gender = NEUTER, Case = NOMINATIVE, Number = PLURAL, PossDial = 0 },
        new PreciseCrasis { Crasis = "to/", CurString = "ta/", Gender = NEUTER, Case = VOCATIVE, Number = PLURAL, PossDial = 0 },
        new PreciseCrasis { Crasis = "to/", CurString = "ta/", Gender = NEUTER, Case = ACCUSATIVE, Number = PLURAL, PossDial = 0 },
        new PreciseCrasis { Crasis = "ta/", CurString = "ta/", Gender = NEUTER, Case = NOMINATIVE, Number = PLURAL, PossDial = 0 },
        new PreciseCrasis { Crasis = "ta/", CurString = "ta/", Gender = NEUTER, Case = VOCATIVE, Number = PLURAL, PossDial = 0 },
        new PreciseCrasis { Crasis = "ta/", CurString = "ta/", Gender = NEUTER, Case = ACCUSATIVE, Number = PLURAL, PossDial = 0 },
        new PreciseCrasis { Crasis = "ta/", CurString = "ta/", Gender = 0, Case = 0, Number = 0, PossDial = 0 },
        new PreciseCrasis { Crasis = "to/", CurString = "to/", Gender = 0, Case = 0, Number = 0, PossDial = 0 }
    };

    private static PossCrasis[] PossCras = new PossCrasis[]
    {
        new PossCrasis { MungedWord = "*)=w", WordStart = "*)/a", PreWord = "w)=", PossDial = 0 },
        new PossCrasis { MungedWord = "*)=w", WordStart = "*)e", PreWord = "w)=", PossDial = 0 },
        new PossCrasis { MungedWord = "ka)", WordStart = "*)a", PreWord = "kai/", PossDial = 0 },
        new PossCrasis { MungedWord = "a(=", WordStart = "a)/", PreWord = "o(", PossDial = 0 },
        new PossCrasis { MungedWord = "a(", WordStart = "a)", PreWord = "o(", PossDial = 0 },
        new PossCrasis { MungedWord = "a(", WordStart = "e)", PreWord = "a(/", PossDial = 0 },
        new PossCrasis { MungedWord = "ei(", WordStart = "ei)", PreWord = "a(/", PossDial = 0 },
        new PossCrasis { MungedWord = "au(", WordStart = "au)", PreWord = "o(", PossDial = 0 },
        new PossCrasis { MungedWord = "dau)", WordStart = "au)", PreWord = "de/", PossDial = 0 },
        new PossCrasis { MungedWord = "dh)", WordStart = "e)", PreWord = "dh/", PossDial = 0 },
        new PossCrasis { MungedWord = "da)", WordStart = "a)", PreWord = "dh/", PossDial = 0 },
        new PossCrasis { MungedWord = "hu(", WordStart = "eu)", PreWord = "h(", PossDial = 0 },
        new PossCrasis { MungedWord = "qat", WordStart = "e(t", PreWord = "tou=", PossDial = 0 },
        new PossCrasis { MungedWord = "qa)/", WordStart = "e(/", PreWord = "to/", PossDial = 0 },
        new PossCrasis { MungedWord = "qoi)", WordStart = "i(", PreWord = "to/", PossDial = 0 },
        new PossCrasis { MungedWord = "qai)", WordStart = "i(", PreWord = "ta/", PossDial = 0 },
        new PossCrasis { MungedWord = "qou)", WordStart = "u(", PreWord = "to/", PossDial = 0 },
        new PossCrasis { MungedWord = "qou(", WordStart = "e(", PreWord = "to/", PossDial = 0 },
        new PossCrasis { MungedWord = "qou)", WordStart = "e(", PreWord = "to/", PossDial = 0 },
        new PossCrasis { MungedWord = "qh)", WordStart = "h(", PreWord = "th=|", PossDial = 0 },
        new PossCrasis { MungedWord = "qh)", WordStart = "h(", PreWord = "tou=", PossDial = 0 },
        new PossCrasis { MungedWord = "qh)", WordStart = "h(", PreWord = "to/", PossDial = 0 },
        new PossCrasis { MungedWord = "qa)", WordStart = "e(", PreWord = "th=|", PossDial = 0 },
        new PossCrasis { MungedWord = "qa)", WordStart = "a(", PreWord = "ta/", PossDial = 0 },
        new PossCrasis { MungedWord = "qa)", WordStart = "e(", PreWord = "tou=", PossDial = 0 },
        new PossCrasis { MungedWord = "qa/t", WordStart = "e(/t", PreWord = "to/", PossDial = 0 },
        new PossCrasis { MungedWord = "kai)", WordStart = "ai)", PreWord = "kai/", PossDial = (Dialect)(DORIC | EPIC) },
        new PossCrasis { MungedWord = "kei)", WordStart = "ei)", PreWord = "kai/", PossDial = 0 },
        new PossCrasis { MungedWord = "kei)", WordStart = "ei)", PreWord = "kai/", PossDial = 0 },
        new PossCrasis { MungedWord = "keu)", WordStart = "eu)", PreWord = "kai/", PossDial = 0 },
        new PossCrasis { MungedWord = "ka)=|", WordStart = "ei)=", PreWord = "kai/", PossDial = 0 },
        new PossCrasis { MungedWord = "ka)|", WordStart = "ai)", PreWord = "kai/", PossDial = 0 },
        new PossCrasis { MungedWord = "ta)|", WordStart = "ai)", PreWord = "ta/", PossDial = 0 },
        new PossCrasis { MungedWord = "ka)=", WordStart = "a)/", PreWord = "kai/", PossDial = 0 },
        new PossCrasis { MungedWord = "ka)", WordStart = "a)", PreWord = "kai/", PossDial = 0 },
        new PossCrasis { MungedWord = "katta", WordStart = "ta", PreWord = "kata/", PossDial = Dialect.DORIC },
        new PossCrasis { MungedWord = "kadd", WordStart = "d", PreWord = "kata/", PossDial = Dialect.EPIC },
        new PossCrasis { MungedWord = "ka)", WordStart = "e)", PreWord = "kai/", PossDial = 0 },
        new PossCrasis { MungedWord = "kw)", WordStart = "o)", PreWord = "kai/", PossDial = 0 },
        new PossCrasis { MungedWord = "kw)", WordStart = "w)", PreWord = "kai/", PossDial = 0 },
        new PossCrasis { MungedWord = "kou)", WordStart = "ou)", PreWord = "kai/", PossDial = 0 },
        new PossCrasis { MungedWord = "kau)", WordStart = "au)", PreWord = "kai/", PossDial = 0 },
        new PossCrasis { MungedWord = "khu)", WordStart = "hu)", PreWord = "kai/", PossDial = 0 },
        new PossCrasis { MungedWord = "moi)", WordStart = "oi)", PreWord = "mou", PossDial = 0 },
        new PossCrasis { MungedWord = "ma)", WordStart = "a)", PreWord = "mh/", PossDial = 0 },
        new PossCrasis { MungedWord = "mh)/", WordStart = "e)", PreWord = "mh/", PossDial = 0 },
        new PossCrasis { MungedWord = "mou)", WordStart = "e)", PreWord = "mou", PossDial = 0 },
        new PossCrasis { MungedWord = "ou(", WordStart = "e)", PreWord = "o(/", PossDial = 0 },
        new PossCrasis { MungedWord = "ou(", WordStart = "o)", PreWord = "o(", PossDial = 0 },
        new PossCrasis { MungedWord = "ou(", WordStart = "e(", PreWord = "o(", PossDial = 0 },
        new PossCrasis { MungedWord = "ou(", WordStart = "u(", PreWord = "o(", PossDial = 0 },
        new PossCrasis { MungedWord = "qw)/", WordStart = "o(/", PreWord = "ta/", PossDial = 0 },
        new PossCrasis { MungedWord = "pottw/s", WordStart = "tw/s", PreWord = "poti/", PossDial = Dialect.DORIC },
        new PossCrasis { MungedWord = "ta)/|", WordStart = "ai)/", PreWord = "to/", PossDial = 0 },
        new PossCrasis { MungedWord = "ta)=", WordStart = "a)/", PreWord = "ta/", PossDial = 0 },
        new PossCrasis { MungedWord = "ta)", WordStart = "a)", PreWord = "ta/", PossDial = 0 },
        new PossCrasis { MungedWord = "ta)", WordStart = "a)", PreWord = "tou=", PossDial = 0 },
        new PossCrasis { MungedWord = "ta)", WordStart = "a)", PreWord = "to/", PossDial = 0 },
        new PossCrasis { MungedWord = "ta)/", WordStart = "*)/a", PreWord = "to/", PossDial = 0 },
        new PossCrasis { MungedWord = "ta)", WordStart = "e)", PreWord = "ta/", PossDial = 0 },
        new PossCrasis { MungedWord = "th)", WordStart = "e)", PreWord = "th=|", PossDial = 0 },
        new PossCrasis { MungedWord = "tau)", WordStart = "au)", PreWord = "tou=", PossDial = 0 },
        new PossCrasis { MungedWord = "tau)", WordStart = "au)", PreWord = "to/", PossDial = 0 },
        new PossCrasis { MungedWord = "tu/xa)gaqh=|", WordStart = "a)gaqh=|", PreWord = "tu/xh|", PossDial = 0 },
        new PossCrasis { MungedWord = "tu/xa)gaqh|", WordStart = "a)gaqh=|", PreWord = "tu/xh|", PossDial = 0 },
        new PossCrasis { MungedWord = "tw)", WordStart = "*)a", PreWord = "tou=", PossDial = 0 },
        new PossCrasis { MungedWord = "tw)", WordStart = "a)", PreWord = "tou=", PossDial = 0 },
        new PossCrasis { MungedWord = "tw)", WordStart = "a)", PreWord = "tou=", PossDial = 0 },
        new PossCrasis { MungedWord = "tw)=", WordStart = "a)/", PreWord = "toi/", PossDial = Dialect.DORIC },
        new PossCrasis { MungedWord = "tw)", WordStart = "w)", PreWord = "to/", PossDial = 0 },
        new PossCrasis { MungedWord = "tw)", WordStart = "h(", PreWord = "to/", PossDial = 0 },
        new PossCrasis { MungedWord = "tw)", WordStart = "o)", PreWord = "tw=|", PossDial = 0 },
        new PossCrasis { MungedWord = "sou)", WordStart = "o(", PreWord = "sou", PossDial = 0 },
        new PossCrasis { MungedWord = "sou)", WordStart = "e(", PreWord = "sou", PossDial = 0 },
        new PossCrasis { MungedWord = "sou)", WordStart = "e)", PreWord = "sou", PossDial = 0 },
        new PossCrasis { MungedWord = "tou)", WordStart = "o)", PreWord = "to/", PossDial = 0 },
        new PossCrasis { MungedWord = "tou)", WordStart = "e)", PreWord = "to/", PossDial = 0 },
        new PossCrasis { MungedWord = "tou)", WordStart = "e)", PreWord = "to/", PossDial = 0 },
        new PossCrasis { MungedWord = "tou)", WordStart = "e)", PreWord = "tou=", PossDial = 0 },
        new PossCrasis { MungedWord = "tou)=", WordStart = "e)/", PreWord = "tou=", PossDial = 0 },
        new PossCrasis { MungedWord = "tou)=", WordStart = "o)/", PreWord = "to/", PossDial = 0 },
        new PossCrasis { MungedWord = "tw)", WordStart = "e)", PreWord = "tw=|", PossDial = 0 },
        new PossCrasis { MungedWord = "tou)", WordStart = "ou)", PreWord = "tou=", PossDial = 0 },
        new PossCrasis { MungedWord = "tou)", WordStart = "e(", PreWord = "to/", PossDial = 0 },
        new PossCrasis { MungedWord = "tw)u", WordStart = "au)", PreWord = "ta/", PossDial = Dialect.IONIC },
        new PossCrasis { MungedWord = "tw)u", WordStart = "au)", PreWord = "to/", PossDial = Dialect.IONIC },
        new PossCrasis { MungedWord = "tw)u", WordStart = "au)", PreWord = "tou=", PossDial = Dialect.IONIC },
        new PossCrasis { MungedWord = "twu)", WordStart = "au)", PreWord = "ta/", PossDial = Dialect.IONIC },
        new PossCrasis { MungedWord = "twu)", WordStart = "au)", PreWord = "to/", PossDial = Dialect.IONIC },
        new PossCrasis { MungedWord = "twu)", WordStart = "au)", PreWord = "tou=", PossDial = Dialect.IONIC },
        new PossCrasis { MungedWord = "tw)", WordStart = "a)", PreWord = "to/", PossDial = Dialect.IONIC },
        new PossCrasis { MungedWord = "tw)", WordStart = "a)", PreWord = "toi/", PossDial = Dialect.DORIC },
        new PossCrasis { MungedWord = "tau)", WordStart = "au)", PreWord = "to/", PossDial = 0 },
        new PossCrasis { MungedWord = "ou(", WordStart = "e)", PreWord = "o(", PossDial = 0 },
        new PossCrasis { MungedWord = "prou)", WordStart = "proe", PreWord = "", PossDial = 0 },
        new PossCrasis { MungedWord = "sumprou", WordStart = "sumproe", PreWord = "", PossDial = 0 },
        new PossCrasis { MungedWord = "cumprou", WordStart = "cumproe", PreWord = "", PossDial = 0 },
        new PossCrasis { MungedWord = "a)ntiprou", WordStart = "a)ntiproe", PreWord = "", PossDial = 0 },
        new PossCrasis { MungedWord = "prou", WordStart = "proe", PreWord = "", PossDial = 0 },
        new PossCrasis { MungedWord = "prou", WordStart = "proo", PreWord = "", PossDial = 0 },
        new PossCrasis { MungedWord = "prwu", WordStart = "proau", PreWord = "", PossDial = 0 },
        new PossCrasis { MungedWord = "e)gw)=i", WordStart = "oi)=", PreWord = "e)gw/", PossDial = 0 },
        new PossCrasis { MungedWord = "e)gw)=|", WordStart = "oi)=", PreWord = "e)gw/", PossDial = 0 },
        new PossCrasis { MungedWord = "e)gw=|", WordStart = "oi)=", PreWord = "e)gw/", PossDial = 0 },
        new PossCrasis { MungedWord = "e)mou)", WordStart = "e)", PreWord = "e)moi", PossDial = 0 },
        new PossCrasis { MungedWord = "kh)", WordStart = "E)", PreWord = "kai/", PossDial = 0 },
        new PossCrasis { MungedWord = "kh)", WordStart = "e)", PreWord = "kai/", PossDial = 0 },
        new PossCrasis { MungedWord = "xh)", WordStart = "h(", PreWord = "kai/", PossDial = 0 },
        new PossCrasis { MungedWord = "xh(", WordStart = "h(", PreWord = "kai/", PossDial = 0 },
        new PossCrasis { MungedWord = "xa)", WordStart = "a(", PreWord = "kai/", PossDial = Dialect.DORIC },
        new PossCrasis { MungedWord = "xa)", WordStart = "e(", PreWord = "kai/", PossDial = 0 },
        new PossCrasis { MungedWord = "xai)", WordStart = "ai(", PreWord = "kai/", PossDial = 0 },
        new PossCrasis { MungedWord = "xoi)", WordStart = "oi(", PreWord = "kai/", PossDial = 0 },
        new PossCrasis { MungedWord = "xau)", WordStart = "au(", PreWord = "kai/", PossDial = 0 },
        new PossCrasis { MungedWord = "xou)", WordStart = "ou(", PreWord = "kai/", PossDial = 0 },
        new PossCrasis { MungedWord = "xu)", WordStart = "u(", PreWord = "kai/", PossDial = 0 },
        new PossCrasis { MungedWord = "xw)", WordStart = "o(", PreWord = "kai/", PossDial = 0 },
        new PossCrasis { MungedWord = "xw(", WordStart = "o(", PreWord = "kai/", PossDial = 0 },
        new PossCrasis { MungedWord = "xw)", WordStart = "w(", PreWord = "kai/", PossDial = 0 },
        new PossCrasis { MungedWord = "w(n", WordStart = "a)n", PreWord = "o(", PossDial = 0 },
        new PossCrasis { MungedWord = "w(/n", WordStart = "a)/n", PreWord = "oi(", PossDial = 0 },
        new PossCrasis { MungedWord = "w(u", WordStart = "au)", PreWord = "o(", PossDial = 0 },
        new PossCrasis { MungedWord = "wu)", WordStart = "au)", PreWord = "o(", PossDial = 0 },
        new PossCrasis { MungedWord = "w(u", WordStart = "au)", PreWord = "oi(", PossDial = 0 },
        new PossCrasis { MungedWord = "w)=gaqe", WordStart = "a)gaqe/", PreWord = "w)=", PossDial = 0 },
        new PossCrasis { MungedWord = "w)=", WordStart = "a)/", PreWord = "w)=", PossDial = 0 },
        new PossCrasis { MungedWord = "w)|", WordStart = "oi)", PreWord = "w)=", PossDial = 0 },
        new PossCrasis { MungedWord = "w)=", WordStart = "o)/", PreWord = "w)=", PossDial = 0 },
        new PossCrasis { MungedWord = "w)", WordStart = "a)", PreWord = "w)=", PossDial = 0 },
        new PossCrasis { MungedWord = "w(=", WordStart = "a)/", PreWord = "oi(", PossDial = 0 },
        new PossCrasis { MungedWord = "w)/", WordStart = "a)/", PreWord = "w)=", PossDial = 0 }
    };

    private static PossCrasis[] LatSync = new PossCrasis[]
    {
        new PossCrasis { MungedWord = "cognor", WordStart = "cognover", PreWord = "", PossDial = 0 },
        new PossCrasis { MungedWord = "ignor", WordStart = "ignover", PreWord = "", PossDial = 0 },
        new PossCrasis { MungedWord = "cognoss", WordStart = "cognoviss", PreWord = "", PossDial = 0 },
        new PossCrasis { MungedWord = "nosse", WordStart = "novisse", PreWord = "", PossDial = 0 },
        new PossCrasis { MungedWord = "copt", WordStart = "coopt", PreWord = "", PossDial = 0 },
        new PossCrasis { MungedWord = "der", WordStart = "deer", PreWord = "", PossDial = 0 },
        new PossCrasis { MungedWord = "des", WordStart = "dees", PreWord = "", PossDial = 0 },
        new PossCrasis { MungedWord = "abin", WordStart = "abis", PreWord = "ne", PossDial = 0 },
        new PossCrasis { MungedWord = "adeon", WordStart = "adeo", PreWord = "ne", PossDial = 0 },
        new PossCrasis { MungedWord = "ain", WordStart = "ais", PreWord = "ne", PossDial = 0 },
        new PossCrasis { MungedWord = "eccam", WordStart = "ecce", PreWord = "eam", PossDial = 0 },
        new PossCrasis { MungedWord = "eccum", WordStart = "ecce", PreWord = "eum", PossDial = 0 },
        new PossCrasis { MungedWord = "eccas", WordStart = "ecce", PreWord = "eas", PossDial = 0 },
        new PossCrasis { MungedWord = "eccos", WordStart = "ecce", PreWord = "eos", PossDial = 0 },
        new PossCrasis { MungedWord = "eccillum", WordStart = "ecce", PreWord = "illum", PossDial = 0 },
        new PossCrasis { MungedWord = "eccillam", WordStart = "ecce", PreWord = "illam", PossDial = 0 },
        new PossCrasis { MungedWord = "eccistum", WordStart = "ecce", PreWord = "istum", PossDial = 0 },
        new PossCrasis { MungedWord = "eccistam", WordStart = "ecce", PreWord = "istam", PossDial = 0 }
    };

    private static int nocrasis = 0;

    public static int CheckCrasis(GkWord Gkword)
    {
        int i;
        string saveword = new string(new char[MAXWORDSIZE]);
        string stringWord = Gkword.Workword;
        string mungedword;
        int rval = 0;

        if (nocrasis != 0) return 0;

        if (CurLang() == Language.LATIN)
        {
            saveword = stringWord;
            for (i = 0; i < MAXWORDSIZE; i++)
            {
                if (stringWord[i] == '\0')
                    break;
                stringWord = stringWord.ToLower();
            }
            for (i = 0; i < LatSync.Length; i++)
            {
                mungedword = LatSync[i].MungedWord;

                if (stringWord[0] == mungedword[0] && !stringWord.Substring(0, mungedword.Length).Equals(mungedword))
                {
                    rval += TestCrasis(Gkword, mungedword, LatSync[i].WordStart, LatSync[i].PreWord, LatSync[i].PossDial);
                }
            }
            return rval;
        }

        for (i = 0; i < PossCras.Length; i++)
        {
            mungedword = PossCras[i].MungedWord;

            if (stringWord[0] == mungedword[0] && !stringWord.Substring(0, mungedword.Length).Equals(mungedword))
            {
                rval += TestCrasis(Gkword, mungedword, PossCras[i].WordStart, PossCras[i].PreWord, PossCras[i].PossDial);
            }
        }
        return rval;
    }

    public static void SetNoCrasis()
    {
        nocrasis = 1;
    }

    public static int TestCrasis(GkWord Gkword, string mungedword, string wordstart, string preword, Dialect possdial)
    {
        string saveword = new string(new char[MAXWORDSIZE]);
        string word1 = new string(new char[MAXWORDSIZE]);
        string word2 = new string(new char[MAXWORDSIZE]);
        Dialect olddial = 0;
        int rval = 0;
        GkWord tmpGkword = new GkWord();

        tmpGkword = Gkword;

        saveword = tmpGkword.Workword;
        tmpGkword.Workword = wordstart + saveword.Substring(mungedword.Length);
        tmpGkword.Crasis = preword;

        olddial = tmpGkword.Dialect;
        tmpGkword.Dialect |= possdial;
        tmpGkword.Stem.Dialect |= possdial;
        rval = CheckString3(tmpGkword);

        if (rval != 0)
        {
            GkAnalysis curanal = tmpGkword.Analysis;
            int i = 0;
            int nanals;

            nanals = tmpGkword.TotalAnalysis;

            for (i = 0; i < nanals; i++)
            {
                curanal = tmpGkword.Analysis[i];
                curanal.Dialect |= possdial;
            }
            Gkword.CopyAnalysis(tmpGkword);
        }
        tmpGkword.Dialect = olddial;
        tmpGkword.Crasis = "";
        tmpGkword.Workword = saveword;

        return rval;
    }

    public static int DoCrasis(GkString gstring, string crasis)
    {
        int gend, num, wcase;
        int saw_this_crasis = 0;
        int i;

        num = gstring.FormInfo.Number;
        gend = gstring.FormInfo.Gender;
        wcase = gstring.FormInfo.Case;

        for (i = 0; i < CrasTab.Length; i++)
        {
            if (crasis.Equals(CrasTab[i].Crasis))
            {
                saw_this_crasis++;
                if (num == CrasTab[i].Number &&
                    ((gend & CrasTab[i].Gender) != 0 || gend == CrasTab[i].Gender) &&
                    ((wcase & CrasTab[i].Case) != 0 || wcase == CrasTab[i].Case))
                {
                    if ((gstring.Dialect & CrasTab[i].PossDial) >= 0)
                    {
                        crasis = CrasTab[i].CurString;
                        return 1;
                    }
                }
            }
        }

        if (saw_this_crasis != 0)
        {
            crasis = "";
            return 0;
        }
        return 1;
    }
}
