using System;

public class CheckNom
{
    public static int checknom(GkWord Gkword)
    {
        int rval;

        if ((Gkword.PrntFlags & PrntFlags.VERBS_ONLY) != 0) return 0;

        if ((rval = checkregnom(Gkword)) != 0)
            return rval;
        return 0;
    }

    public static int checkregnom(GkWord Gkword)
    {
        string workword = Gkword.Workword;
        string half1 = workword;
        int rval = 0;

        Gkword.SetZeroEnd();
        Gkword.Stem = workword;

        rval += gotnom(Gkword);

        for (int i = 0; i < workword.Length; i++)
        {
            Gkword.EndString = workword.Substring(i);
            half1 = workword.Substring(0, i);
            Gkword.Stem = half1;
            rval += gotnom(Gkword);
        }

        return rval;
    }

    private static int gotnom(GkWord Gkword)
    {
        int is_ending = 0;
        int rval = 0;
        string endkeys = "";
        string stemkeys = "";
        string curend = Gkword.EndString;
        GkString curstem = new GkString();

        curend = StripAcc(curend);
        is_ending = chcknend(curend, ref endkeys);

        if (is_ending != 0)
        {
            curstem.GkString = StripAcc(Gkword.Stem);
            if (stemexists(curstem.GkString, endkeys, ref stemkeys, 1))
            {
                rval += StemWorks(Gkword, stemkeys, curstem);
            }
        }

        return rval;
    }

    private static string StripAcc(string input)
    {
        // Placeholder for the actual implementation of StripAcc
        return input;
    }

    private static int chcknend(string curend, ref string endkeys)
    {
        // Placeholder for the actual implementation of chcknend
        return 0;
    }

    private static bool stemexists(string curstem, string endkeys, ref string stemkeys, int v)
    {
        // Placeholder for the actual implementation of stemexists
        return false;
    }

    private static int StemWorks(GkWord Gkword, string stemkeys, GkString curstem)
    {
        // Placeholder for the actual implementation of StemWorks
        return 0;
    }
}

public class GkWord
{
    public string Workword { get; set; }
    public string Stem { get; set; }
    public string EndString { get; set; }
    public PrntFlags PrntFlags { get; set; }

    public void SetZeroEnd()
    {
        // Placeholder for the actual implementation of SetZeroEnd
    }
}

public class GkString
{
    public string GkString { get; set; }
}

[Flags]
public enum PrntFlags
{
    VERBS_ONLY = 1
}
