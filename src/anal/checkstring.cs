using System;
using System.IO;

public class CheckString
{
    private static Dialect WantDialects = Dialect.ALL_DIAL;
    private static gk_word BlankWord, CheckWord;

    public static int teststring(string input)
    {
        return checkstring(input, PrntFlags.NONE, Console.Out);
    }

    public static int checkstring(string input, PrntFlags prntflags, TextWriter fout)
    {
        if (string.IsNullOrWhiteSpace(input) || input.Length >= Constants.MAXWORDSIZE)
            return 0;

        gk_word Gkword = new gk_word();
        Gkword.SetDialect(WantDialects);
        Gkword.SetWorkword(input);
        Gkword.SetPrntflags(prntflags);
        Gkword.SetRawword(Gkword.GetWorkword());

        if (Gkword.GetCurLang() != Language.ITALIAN)
            StandWord(Gkword.GetWorkword());

        StandPhonetics(Gkword);
        CheckString1(Gkword);

        if (prntflags.HasFlag(PrntFlags.LEMCOUNT))
        {
            int nlems = CountLemmas(Gkword);
            Gkword.Free();
            return nlems;
        }

        int nanals = Gkword.GetTotalAnalyses();
        if (prntflags != PrntFlags.NONE && nanals > 0)
        {
            PrintAnalyses(Gkword, prntflags, fout);
        }

        Gkword.Free();
        return nanals;
    }

    private static int CountLemmas(gk_word Gkword)
    {
        int count = 0;
        string prevlem = string.Empty;

        foreach (var analysis in Gkword.GetAnalyses())
        {
            if (analysis.GetLemma().Contains('-'))
                continue;

            if (prevlem != analysis.GetLemma())
            {
                count++;
            }

            prevlem = analysis.GetLemma();
        }

        return count;
    }

    private static void CheckString1(gk_word Gkword)
    {
        string savework = Gkword.GetWorkword();
        if (savework.StartsWith("'"))
        {
            string[] prefixes = { "e)", "a)" };
            foreach (var prefix in prefixes)
            {
                Gkword.SetWorkword(prefix + savework.Substring(1));
                if (CheckString2(Gkword) > 0)
                    return;
            }
        }
        else
        {
            CheckString2(Gkword);
        }
    }

    private static int CheckString2(gk_word Gkword)
    {
        int rval = CheckString3(Gkword);
        if (rval == 0 && Gkword.GetTotalAnalyses() == 0)
        {
            rval = CheckCrasis(Gkword);
        }

        if (Gkword.GetCurLang() == Language.LATIN)
            return Gkword.GetTotalAnalyses();

        if (Gkword.GetDialect().HasFlag(Dialect.HOMERIC | Dialect.IONIC) || !Gkword.GetDialect().HasFlag(Dialect.PROSE))
        {
            Dialect olddial = Gkword.GetDialect();
            gk_string m = new gk_string(Gkword.GetMorphflags());
            gk_string m2 = new gk_string(Gkword.GetMorphflags());

            Gkword.AddMorphflag(MorphFlags.UNAUGMENTED);
            Gkword.AddMorphflagToStem(MorphFlags.UNAUGMENTED);
            if (!Gkword.GetDialect().HasFlag(Dialect.IONIC | Dialect.PROSE))
                Gkword.AddDialect(Dialect.IONIC | Dialect.EPIC);

            Gkword.SetDialect(Gkword.GetDialect() | Dialect.IONIC | Dialect.EPIC);
            rval = CheckString3(Gkword);
            if (rval == 0 && Gkword.GetTotalAnalyses() == 0)
            {
                rval = CheckCrasis(Gkword);
            }

            Gkword.SetDialect(olddial);
            Gkword.SetMorphflags(m.GetMorphflags());
            Gkword.SetMorphflagsToStem(m2.GetMorphflags());

            if (Gkword.GetCurLang() != Language.LATIN && rval == 0 && !Gkword.GetDialect().HasFlag(Dialect.IONIC | Dialect.PROSE))
            {
                Gkword.AddMorphflag(MorphFlags.POETIC);
                Gkword.AddMorphflag(MorphFlags.UNAUGMENTED);
                Gkword.AddMorphflagToStem(MorphFlags.UNAUGMENTED);
                rval = CheckString3(Gkword);
                if (rval == 0 && Gkword.GetTotalAnalyses() == 0)
                {
                    rval = CheckCrasis(Gkword);
                }

                Gkword.SetDialect(olddial);
                Gkword.SetMorphflags(m.GetMorphflags());
                Gkword.SetMorphflagsToStem(m2.GetMorphflags());
            }
        }

        return Gkword.GetTotalAnalyses();
    }

    private static int CheckString3(gk_word Gkword)
    {
        string saveword = Gkword.GetWorkword();
        string workword = Gkword.GetWorkword();
        string wordnoacc = Gkword.GetWorkword();
        StripAccents(ref wordnoacc);

        int rval = CheckWord(Gkword);
        if (rval > 0)
            return rval;

        if (Gkword.GetCurLang() == Language.GREEK)
        {
            if (HasCun(ref workword))
            {
                Gkword.SetWorkword(workword);
                rval += CheckIndecl(Gkword);
                rval += CheckNom(Gkword);
                Gkword.SetWorkword(saveword);
                if (rval > 0)
                    return rval;
            }

            if (HasTt(ref workword))
            {
                Gkword.SetWorkword(workword);
                rval = CheckString4(Gkword);
                Gkword.SetWorkword(saveword);
                if (rval > 0)
                    return rval;
            }
        }

        if (HasApostrophe(workword))
        {
            rval += CheckApostrophe(Gkword);
            if (rval > 0)
                return rval;
        }

        if (Gkword.GetCurLang() == Language.LATIN)
        {
            if (CmpEnd(workword, "ne", out workword))
            {
                Gkword.SetWorkword(workword);
                rval = CheckString3(Gkword);
                if (rval > 0)
                {
                    Gkword.SetWorkword(saveword);
                    return rval;
                }
            }
        }

        Gkword.SetWorkword(saveword);
        return rval;
    }

    private static int CheckString4(gk_word Gkword)
    {
        string saveword = Gkword.GetWorkword();
        string wordnoacc = Gkword.GetWorkword();
        StripAccents(ref wordnoacc);

        int rval = CheckWord(Gkword);
        if (rval > 0)
            return rval;

        if (Gkword.GetCurLang() == Language.GREEK)
        {
            if (HasCun(ref wordnoacc))
            {
                Gkword.SetWorkword(wordnoacc);
                rval += CheckIndecl(Gkword);
                rval += CheckNom(Gkword);
                Gkword.SetWorkword(saveword);
                if (rval > 0)
                    return rval;
            }

            if (HasTt(ref wordnoacc))
            {
                Gkword.SetWorkword(wordnoacc);
                rval = CheckString4(Gkword);
                Gkword.SetWorkword(saveword);
                if (rval > 0)
                    return rval;
            }
        }

        return 0;
    }

    private static bool HasCun(ref string s)
    {
        if (s.Contains("cu"))
        {
            s = s.Replace("cu", "su");
            return true;
        }
        return false;
    }

    private static bool HasTt(ref string s)
    {
        if (s.Contains("tt"))
        {
            s = s.Replace("tt", "ss");
            return true;
        }
        return false;
    }

    private static bool HasApostrophe(string s)
    {
        return s.EndsWith("'");
    }

    private static int CheckApostrophe(gk_word Gkword)
    {
        string saveword = Gkword.GetWorkword();
        int rval = 0;

        if (HasApostrophe(saveword))
        {
            string[] vowels = { "a", "i", "o", "e", "ai" };
            foreach (var vowel in vowels)
            {
                AddApostropheVowel(ref saveword, vowel);
                Gkword.SetWorkword(saveword);
                rval += CheckString3(Gkword);
                Gkword.SetWorkword(saveword);
            }
        }

        return rval;
    }

    private static void AddApostropheVowel(ref string word, string vowel)
    {
        word = word.TrimEnd('\'') + vowel;
        if (CountAccents(word) == 0)
        {
            word += "/";
        }

        if (vowel == "u" || vowel == "i" || vowel == "a")
        {
            word += "^";
        }
    }

    private static void StripAccents(ref string s)
    {
        // Placeholder for the actual implementation of StripAccents
    }

    private static int CountAccents(string s)
    {
        // Placeholder for the actual implementation of CountAccents
        return 0;
    }

    private static int CheckWord(gk_word Gkword)
    {
        // Placeholder for the actual implementation of CheckWord
        return 0;
    }

    private static int CheckIndecl(gk_word Gkword)
    {
        // Placeholder for the actual implementation of CheckIndecl
        return 0;
    }

    private static int CheckNom(gk_word Gkword)
    {
        // Placeholder for the actual implementation of CheckNom
        return 0;
    }

    private static int CheckCrasis(gk_word Gkword)
    {
        // Placeholder for the actual implementation of CheckCrasis
        return 0;
    }

    private static void StandWord(string s)
    {
        // Placeholder for the actual implementation of StandWord
    }

    private static void StandPhonetics(gk_word Gkword)
    {
        // Placeholder for the actual implementation of StandPhonetics
    }

    private static void PrintAnalyses(gk_word Gkword, PrntFlags prntflags, TextWriter fout)
    {
        // Placeholder for the actual implementation of PrintAnalyses
    }
}

public enum PrntFlags
{
    NONE = 0,
    LEMCOUNT = 1
}

public enum Dialect
{
    ALL_DIAL = 1,
    HOMERIC = 2,
    IONIC = 4,
    PROSE = 8,
    EPIC = 16
}

public enum Language
{
    GREEK,
    LATIN,
    ITALIAN
}

public class gk_word
{
    public void SetDialect(Dialect dialect) { }
    public Dialect GetDialect() { return Dialect.ALL_DIAL; }
    public void AddDialect(Dialect dialect) { }
    public void SetWorkword(string workword) { }
    public string GetWorkword() { return string.Empty; }
    public void SetPrntflags(PrntFlags prntflags) { }
    public PrntFlags GetPrntflags() { return PrntFlags.NONE; }
    public void SetRawword(string rawword) { }
    public string GetRawword() { return string.Empty; }
    public Language GetCurLang() { return Language.GREEK; }
    public void AddMorphflag(MorphFlags morphFlags) { }
    public void AddMorphflagToStem(MorphFlags morphFlags) { }
    public void SetMorphflags(MorphFlags morphFlags) { }
    public MorphFlags GetMorphflags() { return MorphFlags.NONE; }
    public void SetMorphflagsToStem(MorphFlags morphFlags) { }
    public int GetTotalAnalyses() { return 0; }
    public gk_analysis[] GetAnalyses() { return new gk_analysis[0]; }
    public void Free() { }
}

public class gk_analysis
{
    public string GetLemma() { return string.Empty; }
}

public class gk_string
{
    public gk_string(MorphFlags morphFlags) { }
    public MorphFlags GetMorphflags() { return MorphFlags.NONE; }
}

public enum MorphFlags
{
    NONE = 0,
    UNAUGMENTED = 1,
    POETIC = 2
}

public static class Constants
{
    public const int MAXWORDSIZE = 256;
}
